tmp_folder="tmp"
if [ -d $tmp_folder ]; then
  echo "清理旧文件 ..."
  rm -rf $tmp_folder
fi
mkdir $tmp_folder

conf_folder="conf"
version=`awk '/<version>[^<]+<\/version>/{gsub(/<version>|<\/version>/,"",$1);print $1;exit;}' pom.xml`

cp -rp $conf_folder/* $tmp_folder

sed -i "s/IMAGE_TAG/$version/g"  $tmp_folder/extension/docker-compose.yml
sed -i "s/IMAGE_TAG/$version/g"  $tmp_folder/helm-charts/values.yaml

base_image_url=`grep "image:" $tmp_folder/extension/docker-compose.yml | awk -F "image: " '{print $NF}' | head -n 1`
base_image_name=`echo $base_image_url | awk -F"/" '{ print $NF }'`
base_image=`echo $base_image_name | awk -F":" '{ print $1 }'`
echo "编译工程源码 ..."
mvn clean package -U -Dmaven.test.skip=true

if [ $? != 0 ]; then
  echo "编译失败"
  exit 1
fi

echo "构建扩展模块镜像 ..."
docker build --build-arg IMAGE_TAG=$version -t $base_image_url .
docker push ${base_image_url}

echo "导出 $base_image_name 镜像 ..."
mkdir $tmp_folder/images
docker save -o $tmp_folder/images/${base_image_name}.tar ${base_image_url}

sed -i '/^version=/d' $tmp_folder/service.inf
echo "version=$version" >> $tmp_folder/service.inf

sed -i '/^created=/d' $tmp_folder/service.inf
create=`date "+%Y-%m-%d %H:%M:%S"`
echo "created=$create" >> $tmp_folder/service.inf

echo "制作扩展模块安装包"
install_file=$base_image-$version.tar.gz
install_offline_file=$base_image-$version-offline.tar.gz

cd $tmp_folder

tar zcf $install_file --exclude=images  ./*
if which md5sum >/dev/null; then
  md5_file_name=${install_file}.md5
  md5sum ${install_file} | awk -F" " '{print "md5: "$1}' > ${md5_file_name}
else
  echo "无法生成 md5 文件"
fi

tar zcf $install_offline_file --exclude='*.tar.gz' ./*
if which md5sum >/dev/null; then
  md5_offline_file_name=${install_offline_file}.md5
  md5sum ${install_offline_file} | awk -F" " '{print "md5: "$1}' > ${md5_offline_file_name}
else
  echo "无法生成 md5 文件"
fi
