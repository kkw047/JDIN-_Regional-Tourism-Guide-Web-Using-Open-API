import requests
import pymysql

# MySQL 데이터베이스 설정
db_config = {
    'host': '61.81.96.151',  # MySQL 서버 주소 (변경된 IP)
    'user': 'outer',  # MySQL 사용자 이름 (변경된 사용자)
    'password': 'outeropensql',  # MySQL 비밀번호 (변경된 비밀번호)
    'database': 'User_Selecte',  # 데이터베이스 이름
    'charset': 'utf8mb4',  # 문자셋 설정
    'cursorclass': pymysql.cursors.DictCursor  # DictCursor로 결과 반환
}


def get_tourist_sites():
    """
    공공데이터 API에서 관광지 데이터를 가져옵니다.
    데이터를 정리하여 리스트 형태로 반환합니다.
    """
    service_key = 'zYQ6z3LDxQw53kNYLivZE0EeBL7erd4d1Yjvy%2BVtS1%2BBrUC7uuOkmfuCl4Gg0pLo9LybOcpASEH98szaOEuLLQ%3D%3D'
    url = f'https://api.odcloud.kr/api/3067368/v1/uddi:b9d25b17-9391-471e-9c7f-aad014581edd?page=1&perPage=10&serviceKey={service_key}'

    try:
        response = requests.get(url)
        response.raise_for_status()  # HTTP 에러 발생 시 예외 처리
        data = response.json()

        # 가져온 데이터 확인
        print("API 응답 데이터:", data)

        # 관광지 데이터를 정리하여 반환
        tourist_sites = []
        for item in data.get('data', []):
            # 이름, 도시, 위치 데이터 정리
            tourist_sites.append({
                'name': item.get('관광지명', '이름 없음'),
                'city': item.get('시군', '도시 없음'),
                'location': item.get('위치', '위치 정보 없음')
            })
        return tourist_sites

    except requests.exceptions.RequestException as e:
        print(f"API 요청 실패: {e}")
        return []


def save_tourist_sites_to_db(tourist_sites):
    """
    관광지 데이터를 데이터베이스에 저장합니다.
    """
    if not tourist_sites:
        print("저장할 데이터가 없습니다.")
        return

    try:
        connection = pymysql.connect(**db_config)
        print("DB 연결 성공!")

        with connection.cursor() as cursor:
            for site in tourist_sites:
                try:
                    # 관광지 중복 확인 및 삽입
                    sql = """
                    INSERT INTO tourist_attraction (name, city, location)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE 
                        city=VALUES(city),
                        location=VALUES(location)
                    """
                    cursor.execute(sql, (
                        site['name'][:255],  # 필드 길이 초과 방지
                        site['city'][:100],  # 필드 길이 제한
                        site['location'][:255]
                    ))
                except Exception as e:
                    print(f"데이터 삽입 오류: {site}, 오류: {e}")
            connection.commit()
            print("관광지 데이터를 데이터베이스에 저장했습니다.")

    except pymysql.MySQLError as e:
        print(f"DB 연결 오류: {e}")
    finally:
        connection.close()


