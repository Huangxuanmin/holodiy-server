import argparse
import alibabacloud_oss_v2 as oss

# 创建命令行参数解析器
parser = argparse.ArgumentParser(description="put object from file sample")

# 添加命令行参数 --region，表示存储空间所在的区域，必需参数
parser.add_argument('--region', default='cn-shanghai', help='The region in which the bucket is located.')

# 添加命令行参数 --bucket，表示存储空间的名称，必需参数
parser.add_argument('--bucket', default='hogel-store', help='The name of the bucket.')

# 添加命令行参数 --endpoint，表示其他服务可用来访问OSS的域名，非必需参数
parser.add_argument('--endpoint', default='oss-cn-shanghai.aliyuncs.com', help='The domain names that other services can use to access OSS')


# 添加命令行参数 --key，表示对象的名称，必需参数
parser.add_argument('--key', default='hogel01.jpg', help='The name of the object.')

# 添加命令行参数 --file_path，表示要上传的本地文件路径，必需参数
parser.add_argument('--file_path', default=r'outputs\hogel_full_001.jpg', help='The path of Upload file.')

def main():
    # 解析命令行参数
    args = parser.parse_args()

    # 从环境变量中加载凭证信息，用于身份验证
    credentials_provider = oss.credentials.EnvironmentVariableCredentialsProvider()

    # 加载SDK的默认配置，并设置凭证提供者
    cfg = oss.config.load_default()
    cfg.credentials_provider = credentials_provider

    # 设置配置中的区域信息
    cfg.region = args.region

    # 如果提供了endpoint参数，则设置配置中的endpoint
    if args.endpoint is not None:
        cfg.endpoint = args.endpoint

    # 使用配置好的信息创建OSS客户端
    client = oss.Client(cfg)

    # 执行上传对象的请求，直接从文件上传
    # 指定存储空间名称、对象名称和本地文件路径
    result = client.put_object_from_file(
        oss.PutObjectRequest(
            bucket=args.bucket,  # 存储空间名称
            key=args.key         # 对象名称
        ),
        args.file_path          # 本地文件路径
    )

    # 输出请求的结果信息，包括状态码、请求ID、内容MD5、ETag、CRC64校验码、版本ID和服务器响应时间
    print(f'status code: {result.status_code},'
          f' request id: {result.request_id},'
          f' content md5: {result.content_md5},'
          f' etag: {result.etag},'
          f' hash crc64: {result.hash_crc64},'
          f' version id: {result.version_id},'
          f' server time: {result.headers.get("x-oss-server-time")},'
    )

# 脚本入口，当文件被直接运行时调用main函数
if __name__ == "__main__":
    main()