echo "清理旧文件 ..."
cd module-demo
rm -rf *.tar.gz *.md5
cd ..

module_version="module.version"
property_file="src/main/resources/application.properties"
has_version=`grep "^$module_version=" $property_file | wc -l`
if [ "$has_version" -ne "0" ]; then
  sed -i '/^module\.version=/d' $property_file
fi
version=`awk '/<version>[^<]+<\/version>/{gsub(/<version>|<\/version>/,"",$1);print $1;exit;}' pom.xml`
echo "$module_version=$version" >> $property_file

sed -i "s/IMAGE_TAG/$version/g"  module-demo/extension/docker-compose.yml
sed -i "s/IMAGE_TAG/$version/g"  module-demo/helm-charts/values.yaml
sed -i "s/IMAGE_TAG/$version/g"  Dockerfile

base_image_url=`grep "image:" module-demo/extension/docker-compose.yml | awk -F "image: " '{print $NF}' | head -n 1`
base_image_name=`echo $base_image_url | awk -F"/" '{ print $NF }'`
base_image=`echo $base_image_name | awk -F":" '{ print $1 }'`
echo "编译工程源码 ..."
mvn clean package -U -Dmaven.test.skip=true

echo "构建扩展模块镜像 ..."
docker build -t $base_image_url .
docker push ${base_image_url}

if [ -d module-demo/images ]; then
  rm -rf module-demo/images
fi
mkdir module-demo/images

echo "导出 $base_image_name 镜像 ..."
docker save -o module-demo/images/${base_image_name}.tar ${base_image_url}

sed -i '/^version=/d' module-demo/service.inf
echo "version=$version" >> module-demo/service.inf

sed -i '/^created=/d' module-demo/service.inf
create=`date "+%Y-%m-%d %H:%M:%S"`
echo "created=$create" >> module-demo/service.inf

echo "制作扩展模块安装包"
install_file=$base_image-$version.tar.gz
install_offline_file=$base_image-$version-offline.tar.gz

cd module-demo

tar zcf $install_file --exclude=images    ./*
md5_file_name=${install_file}.md5
md5sum ${install_file} | awk -F" " '{print "md5: "$1}' > ${md5_file_name}

tar zcf $install_offline_file --exclude='*.tar.gz' ./*
md5_offline_file_name=${install_offline_file}.md5
md5sum ${install_offline_file} | awk -F" " '{print "md5: "$1}' > ${md5_offline_file_name}

cd ..
