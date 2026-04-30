import os

print("当前环境变量检查:")
print("=" * 50)

# 检查阿里云OSS v2 SDK要求的环境变量
oss_vars = [
    "OSS_ACCESS_KEY_ID",
    "OSS_ACCESS_KEY_SECRET", 
    "OSS_SESSION_TOKEN"
]

# 检查阿里云通用环境变量
aliyun_vars = [
    "ALIBABA_CLOUD_ACCESS_KEY_ID",
    "ALIBABA_CLOUD_ACCESS_KEY_SECRET",
    "ALIBABA_CLOUD_SECURITY_TOKEN"
]

print("\n1. 阿里云OSS v2 SDK要求的环境变量:")
for var in oss_vars:
    value = os.getenv(var)
    if value:
        # 显示前4个字符和最后4个字符，中间用*代替
        masked = value[:4] + "*" * (len(value) - 8) + value[-4:] if len(value) > 8 else "***"
        print(f"  {var}: {masked} (已设置)")
    else:
        print(f"  {var}: 未设置")

print("\n2. 阿里云通用环境变量:")
for var in aliyun_vars:
    value = os.getenv(var)
    if value:
        masked = value[:4] + "*" * (len(value) - 8) + value[-4:] if len(value) > 8 else "***"
        print(f"  {var}: {masked} (已设置)")
    else:
        print(f"  {var}: 未设置")

print("\n3. 测试阿里云OSS SDK环境变量提供者:")
try:
    import alibabacloud_oss_v2 as oss
    credentials_provider = oss.credentials.EnvironmentVariableCredentialsProvider()
    print("  ✓ EnvironmentVariableCredentialsProvider 创建成功")
    
    # 尝试获取凭证
    credentials = credentials_provider.get_credentials()
    print(f"  ✓ 成功获取凭证")
    print(f"     Access Key ID: {credentials.access_key_id[:8]}...")
    print(f"     Access Key Secret: {credentials.access_key_secret[:8]}...")
    if credentials.security_token:
        print(f"     Security Token: {credentials.security_token[:8]}...")
    
except Exception as e:
    print(f"  X 错误: {type(e).__name__}: {e}")

print("\n4. 所有环境变量 (包含'ACCESS'或'KEY'的):")
print("-" * 30)
for key, value in os.environ.items():
    if 'ACCESS' in key.upper() or 'KEY' in key.upper() or 'SECRET' in key.upper():
        masked = value[:4] + "*" * (len(value) - 8) + value[-4:] if len(value) > 8 else "***"
        print(f"  {key}: {masked}")