from flask import Flask, render_template, request, jsonify, redirect, url_for
import pymysql
import random
import string
from urllib.parse import unquote
import json

app = Flask(__name__)

# MySQL DB 설정
db_config = {
    'host': '61.81.96.151',  # MySQL 서버 주소
    'user': 'outer',  # MySQL 사용자 이름
    'password': 'outeropensql',  # MySQL 비밀번호
    'database': 'User_Selecte',  # 데이터베이스 이름
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/submit', methods=['POST'])
def submit():
    city = request.form.get('tourist_location')
    count = request.form.get('tourist_sites_count')

    if not city or city == "none":
        return "도시를 선택하세요!", 400
    if not count or int(count) < 1:
        return "관광지 수는 최소 1개 이상이어야 합니다!", 400

    return redirect(url_for('result', city=city, count=count))


@app.route('/result')
def result():
    city = request.args.get('city')
    count = request.args.get('count')

    return render_template('result.html', city=city, count=count)


@app.route('/get_categories', methods=['GET'])
def get_categories():
    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            sql = "SELECT name FROM category"
            cursor.execute(sql)
            categories = [row['name'] for row in cursor.fetchall()]

        return jsonify({"success": True, "categories": categories})
    except Exception as e:
        print(f"오류 발생: {e}")
        return jsonify({"success": False, "error": str(e)})
    finally:
        if 'connection' in locals():
            connection.close()


@app.route('/get_tourist_sites', methods=['GET'])
def get_tourist_sites():
    city = request.args.get('city')
    categories = request.args.get('categories', '')

    print(f"도시: {city}, 카테고리: {categories}")  # 디버깅용 출력

    if not city:
        return jsonify({"success": False, "error": "도시를 지정해야 합니다."}), 400

    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            # SQL 쿼리 수정: mapx, mapy 컬럼 추가
            sql = "SELECT id, name, address, mapx, mapy, image, category FROM tourist_attraction WHERE address LIKE %s"  # category 컬럼 추가
            params = [f"%{city}%"]

            if categories and categories != "전체":
                category_list = categories.split(",")
                like_conditions = []
                for category in category_list:
                    like_conditions.append("category LIKE %s")
                    params.append(f"%{category}%")

                sql += " AND (" + " OR ".join(like_conditions) + ")"

            sql += " ORDER BY RAND() LIMIT 10"
            cursor.execute(sql, params)
            results = cursor.fetchall()

            # 각 관광지 정보에 mapx, mapy 정보를 location 객체에 추가
            for result in results:
                result['location'] = {'mapx': result['mapx'], 'mapy': result['mapy']}

        return jsonify({"success": True, "sites": results})
    except Exception as e:
        print(f"오류 발생: {e}")
        return jsonify({"success": False, "error": str(e)})
    finally:
        if 'connection' in locals():
            connection.close()


@app.route('/process')
def process():
    city = request.args.get('city')
    count = request.args.get('count')
    try:
        count = int(count)
    except ValueError:
        return "잘못된 count 값입니다.", 400

    site_data = {}
    for i in range(1, count + 1):
        location_str = request.args.get(f'site{i}_location')
        if location_str:
            try:
                location_str = unquote(location_str)
                location = json.loads(location_str)
            except json.JSONDecodeError:
                location = {}
        else:
            location = {}

        site_data[i] = {
            'name': request.args.get(f'site{i}_name'),
            'location': location,
            'image': request.args.get(f'site{i}_image'),
            'address': request.args.get(f'site{i}_address'),
            'id': request.args.get(f'site{i}_id')
        }

    return render_template('process.html', city=city, count=count, site_data=site_data)


@app.route('/live', methods=['POST'])
def live():
    city = request.form.get('city')
    count = request.form.get('count')

    try:
        count = int(count)
        if count < 1 or count > 5:  # count 범위 검사 추가 (최대 5개)
            return "관광지 개수는 1~5개여야 합니다.", 400
    except ValueError:
        return "잘못된 count 값입니다.", 400

    # usercode 생성 및 중복 확인
    while True:
        usercode = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        try:
            connection = pymysql.connect(**db_config)
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 FROM user_travel_data WHERE usercode = %s", (usercode,))
                if not cursor.fetchone():
                    break  # 중복되지 않는 usercode 생성 완료
        except Exception as e:
            print(f"usercode 중복 확인 오류: {e}")
        finally:
            if 'connection' in locals():
                connection.close()

    # 사용자 관광지 데이터 저장
    tourist_sites = []
    missions = []
    for i in range(1, count + 1):
        site_id = request.form.get(f'site{i}_id')
        tourist_sites.append(site_id)

        try:
            connection = pymysql.connect(**db_config)
            with connection.cursor() as cursor:
                cursor.execute("SELECT category FROM tourist_attraction WHERE id = %s", (site_id,))
                category_result = cursor.fetchone()
                category = category_result['category'] if category_result else None

                if category:
                    cursor.execute("SELECT id FROM mission WHERE category = %s ORDER BY RAND() LIMIT 1", (category,))
                    mission_id_result = cursor.fetchone()
                    mission_id = mission_id_result['id'] if mission_id_result else None
                    missions.append(mission_id)
                else:
                    missions.append(None)
        except Exception as e:
            print(f"미션 ID 조회 오류: {e}")
            return "오류 발생!", 500
        finally:
            if 'connection' in locals():
                connection.close()

    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            # SQL 쿼리와 매개변수를 동적으로 생성
            columns = ", ".join(
                [f"tourist_site_{i}" for i in range(1, count + 1)] +
                [f"mission_{i}" for i in range(1, count + 1)]
            )
            placeholders = ", ".join(["%s"] * (2 * count))  # 매개변수 자리 표시자 생성

            # 관광지 및 미션 컬럼 외에 초기 상태 컬럼도 추가
            columns += ", " + ", ".join([f"tourist_site_{i}_confirmed" for i in range(1, count + 1)])
            placeholders += ", " + ", ".join(["%s"] * count)

            # 경로 상태 컬럼 추가 (count-1 만큼)
            if count > 1:
                columns += ", " + ", ".join([f"route_{i}_confirmed" for i in range(1, count)])
                placeholders += ", " + ", ".join(["%s"] * (count - 1))

            sql = f"""
                INSERT INTO user_travel_data (usercode, {columns}) 
                VALUES (%s, {placeholders})
            """

            params = [usercode] + tourist_sites + missions

            # 초기 상태 값 추가 (첫 번째 관광지는 "진행중" 상태(2), 나머지는 "대기" 상태(0))
            initial_statuses = [2] + [0] * (count - 1)
            params += initial_statuses

            # 경로 상태 값 추가 (모두 "대기" 상태(0))
            if count > 1:
                route_statuses = [0] * (count - 1)
                params += route_statuses

            cursor.execute(sql, params)  # 데이터 저장
            connection.commit()
    except Exception as e:
        print(f"데이터베이스 삽입 오류: {e}")
        connection.rollback()
        return "오류 발생!", 500
    finally:
        if 'connection' in locals():
            connection.close()

    # 새로 생성된 사용자 코드로 리다이렉트
    return redirect(url_for('live_with_usercode', usercode=usercode, count=count))


@app.route('/live/<usercode>', methods=['GET'])
def live_with_usercode(usercode):
    count = int(request.args.get('count', 0))  # count 값을 가져오고, 없으면 0으로 설정

    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            if count == 0:
                return "선택된 관광지가 없습니다.", 400

            # 관광지 개수에 따라 동적으로 SQL 쿼리 구성
            site_columns = [f'tourist_site_{i}' for i in range(1, count + 1)]
            mission_columns = [f'mission_{i}' for i in range(1, count + 1)]
            site_status_columns = [f'tourist_site_{i}_confirmed' for i in range(1, count + 1)]

            # route 컬럼은 관광지가 2개 이상일 때만 포함
            route_columns = []
            if count > 1:
                route_columns = [f'route_{i}_confirmed' for i in range(1, count)]

            # 모든 컬럼 합치기
            all_columns = site_columns + mission_columns + site_status_columns + route_columns

            sql = f"""
                SELECT {', '.join(all_columns)}
                FROM user_travel_data 
                WHERE usercode = %s
            """
            cursor.execute(sql, (usercode,))
            user_data = cursor.fetchone()

            if not user_data:
                return "잘못된 사용자 코드입니다.", 404

            # tourist_site_id를 사용하여 관광지 정보 가져오기
            tourist_sites = []
            for i in range(1, count + 1):
                site_id = user_data.get(f'tourist_site_{i}')
                if site_id:
                    sql = "SELECT id, name, address, mapx, mapy, image FROM tourist_attraction WHERE id = %s"
                    cursor.execute(sql, (site_id,))
                    site_info = cursor.fetchone()
                    if site_info:
                        tourist_sites.append(site_info)
                    else:
                        tourist_sites.append(None)
                else:
                    tourist_sites.append(None)

            # 마커 데이터 준비
            markers = []
            statuses = []
            for i, site in enumerate(tourist_sites):
                if site:
                    status = user_data.get(f'tourist_site_{i + 1}_confirmed', 0)
                    markers.append({
                        'name': site['name'],
                        'mapx': float(site['mapx']),
                        'mapy': float(site['mapy']),
                        'status': status,
                        'site_number': i + 1
                    })
                    statuses.append(status)
                else:
                    statuses.append(None)

            # 경로 상태 데이터 준비 - 관광지가 2개 이상일 때만
            routes = []
            if count > 1:
                for i in range(1, count):
                    route_status = user_data.get(f'route_{i}_confirmed', 0)
                    routes.append({
                        'status': route_status,
                        'route_number': i
                    })

            # 미션 데이터 준비
            missions = [user_data.get(f'mission_{i}') for i in range(1, count + 1)]
            mission_statuses = [0] * count

        return render_template(
            'live.html',
            usercode=usercode,
            tourist_sites=tourist_sites,
            missions=missions,
            markers=markers,
            statuses=statuses,
            routes=routes if count > 1 else [],  # 관광지가 2개 이상일 때만 routes 전달
            mission_statuses=mission_statuses,
            count=len([site for site in tourist_sites if site])
        )
    except Exception as e:
        print(f"오류 발생: {e}")
        return "오류 발생!", 500
    finally:
        if 'connection' in locals():
            connection.close()

@app.route('/update_status', methods=['POST'])
def update_status():
    data = request.get_json()
    usercode = data['usercode']
    site_number = data['site_number']
    new_status = data['new_status']

    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            # 관광지 상태 업데이트
            sql = f"UPDATE user_travel_data SET tourist_site_{site_number}_confirmed = %s WHERE usercode = %s"
            cursor.execute(sql, (new_status, usercode))
            connection.commit()

            return jsonify({'status': 'success'})
    except pymysql.MySQLError as e:
        print(f"DB error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if 'connection' in locals():
            connection.close()


@app.route('/update_cancel', methods=['POST'])
def update_cancel():
    data = request.json
    usercode = data['usercode']
    item_type = data['item_type']
    item_number = int(data['item_number'])

    # 상태 순서 정의
    status_sequence = [
        'tourist_site_1_confirmed',
        'route_1_confirmed',
        'tourist_site_2_confirmed',
        'route_2_confirmed',
        'tourist_site_3_confirmed'
    ]

    try:
        connection = pymysql.connect(**db_config)
        cursor = connection.cursor()

        # 현재 취소하려는 항목의 인덱스 찾기
        current_index = -1
        for i, status in enumerate(status_sequence):
            if item_type == 'site' and status.startswith(f'tourist_site_{item_number}_'):
                current_index = i
                break
            elif item_type == 'route' and status.startswith(f'route_{item_number}_'):
                current_index = i
                break

        if current_index != -1:
            # 현재 위치는 '진행중(2)'으로, 이후 위치는 모두 '대기(0)'로 설정
            updates = []
            for i, status in enumerate(status_sequence):
                if i == current_index:
                    updates.append(f"{status} = 2")
                elif i > current_index:
                    updates.append(f"{status} = 0")

            if updates:
                sql = f"""UPDATE user_travel_data 
                         SET {', '.join(updates)}
                         WHERE usercode = %s"""
                cursor.execute(sql, (usercode,))
                connection.commit()

        return jsonify({'status': 'success'})

    except Exception as e:
        print(f"Error in update_cancel: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()

@app.route('/update_route_status', methods=['POST'])
def update_route_status():
    data = request.get_json()
    usercode = data['usercode']
    route_number = data['route_number']
    new_status = data['new_status']

    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            # 경로 상태 업데이트
            sql = f"UPDATE user_travel_data SET route_{route_number}_confirmed = %s WHERE usercode = %s"
            cursor.execute(sql, (new_status, usercode))
            connection.commit()

            return jsonify({'status': 'success'})
    except pymysql.MySQLError as e:
        print(f"DB error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if 'connection' in locals():
            connection.close()


if __name__ == '__main__':
    print("스케줄러가 실행 중입니다...")
    app.run(host='0.0.0.0', port=5000, debug=True)
