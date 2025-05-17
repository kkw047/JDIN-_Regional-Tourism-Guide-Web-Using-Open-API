import requests
import pymysql

# MySQL 데이터베이스 설정
db_config = {
    'host': '61.81.96.151',  # MySQL 서버 주소
    'user': 'outer',  # MySQL 사용자 이름
    'password': 'outeropensql',  # MySQL 비밀번호
    'database': 'User_Selecte',  # 데이터베이스 이름
    'charset': 'utf8mb4',  # 문자셋 설정
    'cursorclass': pymysql.cursors.DictCursor  # DictCursor로 결과 반환
}


def get_tourist_sites_from_api():
    """
    공공데이터 API에서 관광지 데이터를 가져옵니다.
    """
    base_url = 'http://apis.data.go.kr/B551011/KorService2/areaBasedSyncList2'
    service_key = 'zYQ6z3LDxQw53kNYLivZE0EeBL7erd4d1Yjvy%2BVtS1%2BBrUC7uuOkmfuCl4Gg0pLo9LybOcpASEH98szaOEuLLQ%3D%3D'
    url = f'{base_url}?serviceKey={service_key}'

    params = {
        'numOfRows': 105,
        'pageNo': 1,
        'MobileOS': 'WIN',
        'MobileApp': 'AppTest',
        '_type': 'json',
        'showflag': 1,
        'arrange': 'C',
        'contentTypeId': 12,
        'areaCode': 33,
        'sigunguCode': 10,
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        # JSON 응답에서 필요한 데이터 추출
        tourist_sites = []
        if 'response' in data and 'body' in data['response'] and 'items' in data['response']['body']:
            items = data['response']['body']['items']['item']
            for item in items:
                tourist_sites.append({
                    'name': item.get('title', '이름 없음')[:255],
                    'addr': item.get('addr1', '주소 정보 없음')[:255],
                    'image': item.get('firstimage', '이미지 정보 없음'),
                    'mapx': item.get('mapx', '좌표 없음'),
                    'mapy': item.get('mapy', '좌표 없음'),
                    'tel': item.get('tel', '전화번호 정보 없음')[:100],
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
        # MySQL 연결
        connection = pymysql.connect(**db_config)
        print("DB 연결 성공!")

        with connection.cursor() as cursor:
            for site in tourist_sites:
                try:
                    # 관광지 데이터를 삽입 또는 업데이트
                    sql = """
                    INSERT INTO tourist_attraction (name, address, image, mapx, mapy, tel)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        address = VALUES(address),
                        image = VALUES(image),
                        mapx = VALUES(mapx),
                        mapy = VALUES(mapy),
                        tel = VALUES(tel)
                    """
                    cursor.execute(sql, (
                        site['name'],
                        site['addr'],
                        site['image'],
                        site['mapx'],
                        site['mapy'],
                        site['tel']
                    ))
                except Exception as e:
                    print(f"데이터 삽입 오류: {site}, 오류: {e}")

            # 데이터베이스에 반영
            connection.commit()
            print(f"{len(tourist_sites)}개의 관광지 데이터를 데이터베이스에 저장했습니다.")

    except pymysql.MySQLError as e:
        print(f"DB 연결 오류: {e}")
    finally:
        connection.close()


if __name__ == '__main__':
    print("API에서 관광지 데이터 가져오는 중...")
    # API에서 관광지 데이터 가져오기
    tourist_sites = get_tourist_sites_from_api()

    print(f"가져온 관광지 데이터 수: {len(tourist_sites)}")
    # 데이터베이스에 저장
    save_tourist_sites_to_db(tourist_sites)
