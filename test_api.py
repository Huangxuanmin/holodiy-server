import requests
import json
import os

# 测试API端点
BASE_URL = "http://localhost:8000"

def test_health():
    """测试健康检查端点"""
    print("测试健康检查端点...")
    response = requests.get(f"{BASE_URL}/api/health")
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.json()}")
    return response.status_code == 200

def test_settings():
    """测试获取设置端点"""
    print("\n测试获取设置端点...")
    response = requests.get(f"{BASE_URL}/api/settings")
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.json()}")
    return response.status_code == 200

def test_estimate():
    """测试预估端点"""
    print("\n测试预估端点...")
    data = {
        "fileCount": 5,
        "totalSize": 1024 * 1024 * 10  # 10MB
    }
    response = requests.post(f"{BASE_URL}/api/estimate", json=data)
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.json()}")
    return response.status_code == 200

def test_hogel_generation():
    """测试hogel生成端点（模拟）"""
    print("\n测试hogel生成端点（模拟）...")
    
    # 创建一个简单的测试文件
    test_file_path = "test_image.jpg"
    
    # 如果没有测试文件，创建一个简单的图像
    if not os.path.exists(test_file_path):
        from PIL import Image
        img = Image.new('RGB', (100, 100), color='red')
        img.save(test_file_path)
        print(f"创建测试文件: {test_file_path}")
    
    try:
        # 准备测试数据
        files = {'files': open(test_file_path, 'rb')}
        data = {
            'C': '10',
            'width': '500',
            'height': '500',
            'quality': '95'
        }
        
        response = requests.post(f"{BASE_URL}/api/generate-hogel", files=files, data=data)
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
            return result.get('success', False)
        else:
            print(f"错误响应: {response.text}")
            return False
            
    except Exception as e:
        print(f"测试失败: {e}")
        return False
    finally:
        if os.path.exists(test_file_path):
            os.remove(test_file_path)
            print(f"清理测试文件: {test_file_path}")

def main():
    """运行所有测试"""
    print("开始测试 Hogel API 服务...")
    print(f"API地址: {BASE_URL}")
    
    tests_passed = 0
    tests_failed = 0
    
    # 测试1: 健康检查
    if test_health():
        tests_passed += 1
    else:
        tests_failed += 1
    
    # 测试2: 获取设置
    if test_settings():
        tests_passed += 1
    else:
        tests_failed += 1
    
    # 测试3: 预估
    if test_estimate():
        tests_passed += 1
    else:
        tests_failed += 1
    
    # 测试4: hogel生成（模拟）
    print("\n注意: hogel生成测试需要上传真实图像文件")
    print("您可以通过前端界面 http://localhost:8000 进行完整测试")
    
    print(f"\n测试结果: 通过 {tests_passed}/3, 失败 {tests_failed}/3")
    
    if tests_failed == 0:
        print("所有基本API测试通过！")
        print("\n下一步:")
        print("1. 访问 http://localhost:8000 使用前端界面")
        print("2. 上传图像文件（支持拖放）")
        print("3. 配置hogel参数")
        print("4. 点击'生成Hogel'按钮")
        print("5. 查看生成结果")
    else:
        print("部分测试失败，请检查Flask服务器是否正常运行")

if __name__ == "__main__":
    main()