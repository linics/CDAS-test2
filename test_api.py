import requests

# 登录
login_response = requests.post(
    'http://127.0.0.1:8000/api/v2/auth/login',
    data={'username': 'teacher1', 'password': 'password123'}
)

print(f"登录状态: {login_response.status_code}")

if login_response.status_code == 200:
    token = login_response.json()['access_token']
    print(f"Token: {token[:100]}...")
    
    # 获取作业列表
    assignments_response = requests.get(
        'http://127.0.0.1:8000/api/v2/assignments/',
        headers={'Authorization': f'Bearer {token}'}
    )
    
    print(f"\n作业列表API状态: {assignments_response.status_code}")
    print(f"响应: {assignments_response.text}")
else:
    print(f"登录失败: {login_response.text}")
