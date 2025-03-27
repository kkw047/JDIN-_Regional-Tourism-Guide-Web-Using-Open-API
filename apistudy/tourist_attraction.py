import requests
import pymysql

db_config = {
    'host': '34.85.84.74',  # MySQL 서버 주소
    'user': 'root',  # MySQL 사용자 이름
    'password': 'woohaha4361!',  # MySQL 비밀번호
    'database': 'food_location',  # 데이터베이스 이름
    'charset': 'utf8mb4',
}

def get_tourist_sites():
    url = "https://api.example.com/tourist_sites"  # 실제 API URL
    response = requests.get(url)
    data = response.json()['data']

    result = []
    for item in data:
        result.append({
            'name': item['관광지명'],
            'city': item['시군'],
            'location': item['위치']
        })

    return result

#
# DB에 관광지 데이터를 저장하는 함수
def save_to_db(data):
    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            for item in data:
                sql = """
                INSERT INTO tourist_attraction (name, city, location)
                VALUES (%s, %s, %s)
                """
                cursor.execute(sql, (item['name'], item['city'], item['location']))
            connection.commit()
    except Exception as e:
        print(f"DB 저장 오류: {e}")
    finally:
        connection.close()
