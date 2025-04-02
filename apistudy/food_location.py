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



def get_food_data():
    """
    공공데이터 API에서 청주와 충주 음식 데이터를 가져옵니다.
    데이터를 정리하여 리스트 형태로 반환합니다.
    """
    service_key = 'zYQ6z3LDxQw53kNYLivZE0EeBL7erd4d1Yjvy%2BVtS1%2BBrUC7uuOkmfuCl4Gg0pLo9LybOcpASEH98szaOEuLLQ%3D%3D'

    # API 주소 정의
    cheongju_url = f'https://api.odcloud.kr/api/3033595/v1/uddi:74266317-2cd8-4b3d-8682-d72062ac1743?page=1&perPage=10&serviceKey={service_key}'
    chungju_url = f'https://api.odcloud.kr/api/3037407/v1/uddi:050eceee-1dde-4be2-ac6b-ef812b73ec8f_201909101500?page=1&perPage=10&serviceKey={service_key}'

    food_data = []

    # 청주 데이터 가져오기
    try:
        response = requests.get(cheongju_url)
        response.raise_for_status()
        for item in response.json().get('data', []):
            food_data.append({
                'name': item.get('업소명', '이름 없음'),
                'type': None,  # 타입 정보가 없으므로 기본값 설정
                'location': item.get('소재지(지번)', '').lstrip('충청북도')
            })
    except requests.exceptions.RequestException as e:
        print(f"청주 음식 데이터 가져오기 실패: {e}")

    # 충주 데이터 가져오기
    try:
        response = requests.get(chungju_url)
        response.raise_for_status()
        for item in response.json().get('data', []):
            food_data.append({
                'name': item.get('업소명', '이름 없음'),
                'type': None,
                'location': item.get('소재지(도로명)', '').lstrip('충청북도')
            })
    except requests.exceptions.RequestException as e:
        print(f"충주 음식 데이터 가져오기 실패: {e}")

    return food_data


def save_food_data_to_db(food_data):
    """
    음식 데이터를 데이터베이스에 저장합니다.
    """
    if not food_data:
        print("저장할 음식 데이터가 없습니다.")
        return

    try:
        connection = pymysql.connect(**db_config)
        print("DB 연결 성공!")

        with connection.cursor() as cursor:
            for food in food_data:
                sql = """
                INSERT INTO food_location (name, type, location)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                    type=VALUES(type),
                    location=VALUES(location)
                """
                cursor.execute(sql, (food['name'], food['type'], food['location']))
            connection.commit()
            print(f"총 {len(food_data)}개의 음식 데이터를 데이터베이스에 저장했습니다.")

    except pymysql.MySQLError as e:
        print(f"DB 저장 오류: {e}")
    finally:
        connection.close()


def init_food_data():
    """
    앱 실행 시 한 번 실행되는 초기화 함수. 음식 데이터를 가져와 DB에 저장합니다.
    """
    print("====== 청주와 충주의 음식 데이터를 가져오는 중입니다... ======")
    food_data = get_food_data()
    print(f"가져온 음식 데이터: {len(food_data)}개의 데이터")

    save_food_data_to_db(food_data)
    print("음식 데이터를 데이터베이스에 저장했습니다.")
