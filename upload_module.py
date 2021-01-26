#!/usr/bin/python
# coding=utf-8
import os, tarfile
import sys
import json
import uuid
import argparse
import subprocess


major_version = sys.version[0]
if major_version == '2':
    from urllib import urlretrieve
    import urllib2 as urlreq
    reload(sys)
    sys.setdefaultencoding('utf8')
else:
    import urllib.request as urlreq
    from urllib.request import urlretrieve

DEFAULT_F2C_DIR = '/tmp/f2cextension'
DEFAULT_NEXUS_USE = 'admin'
DEFAULT_NEXUS_PASSWD = 'admin123'
DEFAULT_NEXUS_URL = 'http://localhost:8081'
DEFAULT_DOCKER_REGISTRY_URL = 'http://localhost:8082'
DEFAULT_INDXSERVER_URI = '/repository/cmp-raw-hosted/json/data.js'

DEFAULT_LOCAL_REGISTRY_PORT = '8082'

parser = argparse.ArgumentParser(description='manual to this script')
parser.add_argument('--module-file', type=str, default=None)
parser.add_argument('--nexus-url', type=str, default=DEFAULT_NEXUS_URL)
parser.add_argument('--docker-registry', type=str, default=DEFAULT_DOCKER_REGISTRY_URL)
parser.add_argument('--nexus-user', type=str, default=DEFAULT_NEXUS_USE)
parser.add_argument('--nexus-passwd', type=str, default=DEFAULT_NEXUS_PASSWD)
args = parser.parse_args()

module_info = {}

if(args.module_file is None):
    print("Module file name can not be empty!")
    print("Use: upload_module.py --module-file MODULE_FILE_NAME")
    os._exit(0)

args.module_file = os.path.join(os.getcwd(), args.module_file)

def create_temp_file():
    isExists=os.path.exists(DEFAULT_F2C_DIR)
    if not isExists:
        os.makedirs(DEFAULT_F2C_DIR)
    module_temp_dir = DEFAULT_F2C_DIR + '/' + str(uuid.uuid4())
    os.makedirs(module_temp_dir)
    os.chdir(module_temp_dir)
    module_info['module_temp_dir'] = module_temp_dir
    print("create temp dir: " + module_temp_dir)

def uncompress_module_file():
    print("uncompress module file: " + args.module_file)
    try:
        t = tarfile.open(args.module_file, "r:gz")
        names = t.getnames()
        for name in names:
            t.extract(name, path=module_info['module_temp_dir'])
    except Exception as e:
        print(e)
        os._exit(1)
    with open(module_info['module_temp_dir'] + '/service.inf', 'r') as file:
        for line in file:
            key = line.split('=')[0].strip()
            if 'module' == key:
                module_info['module'] = line.split('=')[1].strip()
            if 'name' == key:
                module_info['name'] = line.split('=')[1].strip()
            if 'module_description' == key:
                module_info['module_description'] = line.split('=')[1].strip()
            if 'created' == key:
                module_info['created'] = line.split('=')[1].strip()
            if 'version' == key:
                module_info['version'] = line.split('=')[1].strip()
            if 'version_description' == key:
                module_info['version_description'] = line.split('=')[1].strip()

    if os.path.isfile(module_info['module_temp_dir'] + '/service.ico'):
        module_info['service_ico'] = True
        os.rename(module_info['module_temp_dir'] + '/service.ico', module_info['module_temp_dir'] + '/' + module_info['module'] + '.ico')
    else:
        module_info['service_ico'] = False

    try:
        with tarfile.open(module_info['module'] + '.tar.gz', "w:gz") as tar:
            tar.add('./helm-charts')
            tar.add('./extension')
        return True
    except Exception as e:
        print(e)
        os._exit(1)

    return module_info

def down_file():
    print("down file: " + args.nexus_url + DEFAULT_INDXSERVER_URI)
    passwdmgr = urlreq.HTTPPasswordMgrWithDefaultRealm()
    passwdmgr.add_password(None, args.nexus_url + DEFAULT_INDXSERVER_URI, args.nexus_user, args.nexus_passwd)
    httpauth_handler = urlreq.HTTPBasicAuthHandler(passwdmgr)
    opener = urlreq.build_opener(httpauth_handler)
    urlreq.install_opener(opener)
    try:
        if major_version == '3':
            urlretrieve(args.nexus_url + DEFAULT_INDXSERVER_URI, module_info['module_temp_dir'] + '/data.js')
        else:
            sourcefile = urlreq.urlopen(args.nexus_url + DEFAULT_INDXSERVER_URI)
            with open(module_info['module_temp_dir'] + '/data.js', 'w') as file:
                while True:
                    read = sourcefile.read(1024 * 5)
                    if len(read) == 0:
                        break
                    file.write(read)
    except Exception as e:
        print("Cant not downlaod indexserver, {}", e)

def modify_basic_module_info():
    with open(module_info['module_temp_dir'] + '/data.js', 'r') as file:
        origin_data = file.read()

    index_server_data = origin_data.split("let templateDate")[1].strip().split('=')[1].strip()
    json_data = json.loads(index_server_data)
    basic_data = json_data['basic']
    find_module = None
    module_info['find_module'] = False
    for module in basic_data:
        if(module['module'] == module_info['module']):
            find_module = module
            module_info['find_module'] = True

    module_version = {}
    module_version['revision'] = module_info['version']
    module_version['description'] = module_info['version_description']
    module_version['created'] = module_info['created']
    module_version['downloadUrl'] = 'download/' + module_info['module'] + '/' + module_info['module'] + '-' + module_info[
        'version'] + '.tar.gz'

    if(find_module is None):
        find_module = {}
        find_module['module'] = module_info['module']
        find_module['name'] = module_info['name']
        find_module['summary'] = module_info['module_description']
        find_module['icon'] = 'image/' + module_info['module'] + '.ico'
        find_module['overview'] = module_info['module_description']
        find_module['revisions'] = []
        find_module['revisions'].append(module_version)
        basic_data.append(find_module)
    else:
        verison = None
        for v in find_module['revisions']:
            if v['revision'] == module_info['version']:
                v['description'] = module_info['version_description']
                v['created'] = module_info['created']
                verison = v
        if verison is None:
            find_module['revisions'].append(module_version)

    json_data['basic'] = basic_data

    with open(module_info['module_temp_dir'] + '/data.js', 'w') as file:
        file.write("let templateDate = ")
        if major_version == '2':
            file.write(json.dumps(json_data, indent=4).encode('utf-8', 'ignore').decode('unicode_escape'))
        else:
            file.write(json.dumps(json_data, indent=4, ensure_ascii=False))

def load_image():

    if os.path.isdir(module_info['module_temp_dir'] + '/images'):
        for filename in os.listdir(module_info['module_temp_dir'] + '/images'):
            cmd = "docker load -i " + module_info['module_temp_dir'] + '/images/' + filename
            print(cmd)
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
            p.wait()
            print(p.stdout.read())
        os.system('docker login {0} -u {1} -p {2}'.format(args.docker_registry, args.nexus_user, args.nexus_passwd))
        docker_compose = module_info['module_temp_dir'] + '/extension/docker-compose.yml'
        image_command = "grep 'image:' %(docker_compose)s  | awk -F 'image: ' '{print $NF}'" % {'docker_compose': docker_compose}
        p = subprocess.Popen(image_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=1, shell=True)
        p.wait()
        for image in p.stdout.read().splitlines():
            [registry_server, image_path] = image.split('/', 1)
            local_image_tag = '{0}:{1}/{2}'.format(args.nexus_url.split('//')[1].split(':')[0], DEFAULT_LOCAL_REGISTRY_PORT, image_path)
            os.system('docker tag {0} {1}'.format(image, local_image_tag))
            print('docker push {0}'.format(local_image_tag))
            os.system('docker push {0}'.format(local_image_tag))

def upload_file():
    if module_info['service_ico']:
        print("upload " + module_info['module'] + '.ico')
        upload_service_ico = "curl -u %(user)s:%(password)s -X POST '%(nexus_url)s/service/rest/v1/components?repository=cmp-raw-hosted'" \
                       " -H 'accept: application/json' -H 'Content-Type: multipart/form-data' -F 'raw.directory=%(directory)s' " \
                       "-F 'raw.asset1=@%(asset)s'  -F 'raw.asset1.filename=%(filename)s' " \
                       % \
                       {'user': args.nexus_user, 'password': args.nexus_passwd, 'nexus_url': args.nexus_url,
                        'directory': 'image', 'asset':  module_info['module_temp_dir'] + '/' + module_info['module'] + '.ico', 'filename': module_info['module'] + '.ico'}
        p = subprocess.Popen(upload_service_ico, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=1, shell=True)
        p.wait()
        print(p.stdout.read())

    print("upload " + '/data.js')
    upload_index = "curl -u %(user)s:%(password)s -X POST '%(nexus_url)s/service/rest/v1/components?repository=cmp-raw-hosted'" \
                    " -H 'accept: application/json' -H 'Content-Type: multipart/form-data' -F 'raw.directory=%(directory)s' " \
                   "-F 'raw.asset1=@%(asset)s'  -F 'raw.asset1.filename=%(filename)s' " \
                   % \
                {'user': args.nexus_user, 'password': args.nexus_passwd, 'nexus_url': args.nexus_url,
                 'directory': 'json', 'asset': module_info['module_temp_dir'] + '/data.js',
                 'filename': 'data.js'}
    p = subprocess.Popen(upload_index, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=1, shell=True)
    p.wait()
    print(p.stdout.read())

    print("upload " + module_info['module'] + '.tar.gz')
    upload_module_file = "curl -u %(user)s:%(password)s -X POST '%(nexus_url)s/service/rest/v1/components?repository=cmp-raw-hosted'" \
                    " -H 'accept: application/json' -H 'Content-Type: multipart/form-data' -F 'raw.directory=%(directory)s' " \
                    "-F 'raw.asset1=@%(asset)s'  -F 'raw.asset1.filename=%(filename)s' " \
                    % \
                    {'user': args.nexus_user, 'password': args.nexus_passwd, 'nexus_url': args.nexus_url,
                     'directory': 'download/' + module_info['module'], 'asset': module_info['module_temp_dir'] + '/' + module_info['module'] + '.tar.gz',
                     'filename': module_info['module']  + '-' + module_info['version'] + '.tar.gz'}
    p = subprocess.Popen(upload_module_file, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=1, shell=True)
    p.wait()
    print(p.stdout.read())

if __name__ == '__main__':
    create_temp_file()
    uncompress_module_file()
    down_file()
    modify_basic_module_info()
    load_image()
    upload_file()