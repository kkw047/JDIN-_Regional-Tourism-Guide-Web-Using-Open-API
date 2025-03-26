import requests
import pymysql

# DB 설정
db_config = {
    'host': '34.85.84.74',  # MySQL 서버 주소
    'user': 'root',  # MySQL 사용자 이름
    'password': 'woohaha4361!',  # MySQL 비밀번호
    'database': 'food_location',  # 데이터베이스 이름
    'charset': 'utf8mb4',
}

# 청주시 음식 데이터 가져오는 함수
def get_Cheongju():
    service_key = '<YOUR_SERVICE_KEY>'  # API 키를 여기에 삽입
    url = f'https://api.odcloud.kr/api/3033595/v1/uddi:74266317-2cd8-4b3d-8682-d72062ac1743?page=1&perPage=10&serviceKey={service_key}'
    response = requests.get(url)
    data = response.json()['data']

    result = []
    for item in data:
        result.append({
            'name': item['업소명'],
            'type': None,  # 타입 정보는 없으므로 기본값 설정
            'location': item['소재지(지번)'].lstrip('충청북도')
        })

    return result


# 충주시 음식 데이터 가져오는 함수
def get_Chungju():
    service_key = '<YOUR_SERVICE_KEY>'  # API 키를 여기에 삽입
    url = f'https://api.odcloud.kr/api/3037407/v1/uddi:050eceee-1dde-4be2-ac6b-ef812b73ec8f_201909101500?page=1&perPage=10&serviceKey={service_key}'
    response = requests.get(url)
    data = response.json()['data']

    result = []
    for item in data:
        result.append({
            'name': item['업소명'],
            'type': None,  # 타입 정보는 없으므로 기본값 설정
            'location': item['소재지(도로명)'].lstrip('충청북도')
        })

    return result


# DB에 음식 데이터를 저장하는 함수
def save_to_db(data):
    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            for item in data:
                sql = """
                INSERT INTO food_location (name, type, location)
                VALUES (%s, %s, %s)
                """
                cursor.execute(sql, (item['name'], item['type'], item['location']))
            connection.commit()
    except Exception as e:
        print(f"DB 저장 오류: {e}")
    finally:
        connection.close()

