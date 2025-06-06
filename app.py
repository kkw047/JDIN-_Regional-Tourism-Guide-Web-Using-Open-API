from flask import Flask, render_template, request, jsonify, redirect, url_for
import pymysql
import random
import string
from urllib.parse import unquote
import json
import sys  # submit_review에서 사용
from urllib.parse import unquote
from flask import send_from_directory
import os

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
    # 캐러셀에 표시할 관광지 ID 목록
    carousel_site_ids = [1, 2, 3, 4, 5, 6]
    carousel_data = []

    # 각 ID에 해당하는 관광지 정보를 DB에서 가져옴
    for site_id in carousel_site_ids:
        site_info = get_site_details_by_id(site_id)
        if site_info:
            carousel_data.append(site_info)

    return render_template('index.html', carousel_data=carousel_data)


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
    connection = None
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
        if connection and connection.open:
            connection.close()


@app.route('/get_tourist_sites', methods=['GET'])
def get_tourist_sites():
    city = request.args.get('city')
    categories = request.args.get('categories', '')

    print(f"도시: {city}, 카테고리: {categories}")  # 디버깅용 출력

    if not city:
        return jsonify({"success": False, "error": "도시를 지정해야 합니다."}), 400
    connection = None
    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            sql = """
                SELECT ta.id, ta.name, ta.address, ta.mapx, ta.mapy, ta.image, ta.category,
                    ROUND(AVG(r.rating), 1) AS average_rating
                FROM tourist_attraction ta
                LEFT JOIN review r ON ta.id = r.tourist_attraction_id
                WHERE ta.address LIKE %s
                """
            params = [f"%{city}%"]

            if categories and categories != "전체":
                category_list = categories.split(",")
                like_conditions = []
                for category_item in category_list:
                    like_conditions.append("category LIKE %s")
                    params.append(f"%{category_item}%")  # category -> category_item

                sql += " AND (" + " OR ".join(like_conditions) + ")"
            sql += " GROUP BY ta.id ORDER BY RAND() LIMIT 100"
            cursor.execute(sql, params)
            results = cursor.fetchall()

            for res_item in results:  # result -> res_item
                res_item['location'] = {'mapx': res_item['mapx'], 'mapy': res_item['mapy']}
                if res_item['average_rating'] is None:
                        res_item['average_rating'] = 0.0


        return jsonify({"success": True, "sites": results})
    except Exception as e:
        print(f"오류 발생: {e}")
        return jsonify({"success": False, "error": str(e)})
    finally:
        if connection and connection.open:
            connection.close()




@app.route('/process')
def process():
    city = request.args.get('city')
    count_str = request.args.get('count')  # count -> count_str
    try:
        count = int(count_str)  # count_str 사용
    except ValueError:
        return "잘못된 count 값입니다.", 400

    site_data = {}
    for i in range(1, count + 1):
        location_str = request.args.get(f'site{i}_location')
        location = {}  # 기본값 초기화
        if location_str:
            try:
                location_str_decoded = unquote(location_str)  # unquote(location_str)
                location = json.loads(location_str_decoded)  # location_str_decoded
            except json.JSONDecodeError:
                print(f"Warning: JSONDecodeError for site{i}_location: {location_str}")
                location = {}
        # else: location은 이미 {}로 초기화됨

        site_id = request.args.get(f'site{i}_id')
        print(f"[DEBUG] site{i}_id = {site_id}")  # site_id 로그 확인

        if site_id:
            try:
                connection = pymysql.connect(**db_config)
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT name, address, image, time, money 
                        FROM tourist_attraction 
                        WHERE id = %s
                    """, (site_id,))
                    result = cursor.fetchone()
                    print(f"[DEBUG] DB result for site{i}_id={site_id}: {result}")
                    if result:
                        site_info = result
            except Exception as e:
                print(f"[ERROR] DB 조회 실패 (site_id={site_id}): {e}")
            finally:
                if connection and connection.open:
                    connection.close()

        site_data[i] = {
            'name': site_info.get('name', '정보 없음'),
            'location': location,
            'image': site_info.get('image'),
            'address': site_info.get('address', '정보 없음'),
            'id': site_id,
            'time': site_info.get('time', '정보 없음'),
            'money': site_info.get('money', '정보 없음')
        }

    return render_template('process.html', city=city, count=count, site_data=site_data)


@app.route('/live', methods=['GET'])
def live_redirect():
    usercode = request.args.get('code')
    if not usercode:
        return "사용자 코드가 필요합니다.", 400
    connection = None
    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            sql = """
                SELECT tourist_site_1, tourist_site_2, tourist_site_3
                FROM user_travel_data
                WHERE usercode = %s
            """
            cursor.execute(sql, (usercode,))
            row = cursor.fetchone()
            print("row:", row)

            if not row:
                return "잘못된 사용자 코드입니다.", 404

            determined_count = 0  # count -> determined_count
            for i in range(1, 4):
                if row.get(f'tourist_site_{i}') is not None:
                    determined_count += 1
                else:
                    break

            if determined_count == 0:
                return "선택된 관광지가 없습니다.", 400

            return redirect(url_for('live_with_usercode', usercode=usercode, count=determined_count))
    except Exception as e:
        print(f"Error in live_redirect: {e}")
        return "오류 발생!", 500
    finally:
        if connection and connection.open:
            connection.close()


@app.route('/live', methods=['POST'])
def live():
    city = request.form.get('city')
    count_str = request.form.get('count')

    try:
        count = int(count_str)
        if not (1 <= count <= 5):  # Ensure count is within a reasonable range, e.g., 1-5
            return "관광지 개수는 1~5개여야 합니다.", 400
    except ValueError:
        return "잘못된 count 값입니다.", 400

    usercode = ''
    while True:
        usercode = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        try:
            db_conn_outer = pymysql.connect(**db_config)
            with db_conn_outer.cursor() as cursor:
                cursor.execute("SELECT 1 FROM user_travel_data WHERE usercode = %s", (usercode,))
                if not cursor.fetchone():
                    break
        except Exception as e:
            print(f"usercode 중복 확인 오류: {e}")
            return "사용자 코드 생성 중 오류가 발생했습니다.", 500
        finally:
            if db_conn_outer and db_conn_outer.open:
                db_conn_outer.close()

    tourist_sites_ids_from_form = []
    for i in range(1, count + 1):
        site_id = request.form.get(f'site{i}_id')
        tourist_sites_ids_from_form.append(site_id)

    missions = []

    db_conn_inner = None
    try:
        db_conn_inner = pymysql.connect(**db_config)
        with db_conn_inner.cursor() as cursor:
            cursor.execute("SELECT id, category FROM mission")
            all_missions = cursor.fetchall()

            normalized_all_mission_categories = {}
            for mission_data in all_missions:
                mission_id = mission_data['id']
                raw_mission_category = mission_data['category']
                if raw_mission_category:
                    normalized_categories = {cat.strip().lower() for cat in raw_mission_category.split(',') if
                                             cat.strip()}
                    normalized_all_mission_categories[mission_id] = normalized_categories
                else:
                    normalized_all_mission_categories[mission_id] = set()

            for i in range(count):
                site_id = tourist_sites_ids_from_form[i]
                mission_id_to_add = None
                if site_id:
                    cursor.execute("SELECT category FROM tourist_attraction WHERE id = %s", (site_id,))
                    site_category_result = cursor.fetchone()

                    if site_category_result and site_category_result['category']:
                        raw_site_category = site_category_result['category']
                        site_categories = {cat.strip().lower() for cat in raw_site_category.split(',') if
                                           cat.strip()}

                        matching_missions = []
                        for mission_data in all_missions:
                            mission_id = mission_data['id']
                            mission_categories = normalized_all_mission_categories.get(mission_id, set())
                            if site_categories and (site_categories & mission_categories):
                                matching_missions.append(mission_id)

                        if matching_missions:
                            mission_id_to_add = random.choice(matching_missions)
                        else:
                            if all_missions:
                                mission_id_to_add = random.choice([m['id'] for m in all_missions])
                            else:
                                mission_id_to_add = None
                    else:
                        mission_id_to_add = None
                else:
                    mission_id_to_add = None
                missions.append(mission_id_to_add)
    except Exception as e:
        while len(missions) < count:
            missions.append(None)
    finally:
        if db_conn_inner and db_conn_inner.open:
            db_conn_inner.close()

    while len(missions) < count:
        missions.append(None)
    while len(tourist_sites_ids_from_form) < count:
        tourist_sites_ids_from_form.append(None)

    db_conn_insert = None
    try:
        db_conn_insert = pymysql.connect(**db_config)
        with db_conn_insert.cursor() as cursor:
            ts_cols = [f"tourist_site_{i}" for i in range(1, count + 1)]
            m_cols = [f"mission_{i}" for i in range(1, count + 1)]
            m_conf_cols = [f"mission_{i}_confirmed" for i in range(1, count + 1)]
            ts_conf_cols = [f"tourist_site_{i}_confirmed" for i in range(1, count + 1)]
            r_conf_cols = [f"route_{i}_confirmed" for i in range(1, count)] if count > 1 else []

            all_columns_list = ts_cols + m_cols + m_conf_cols + ts_conf_cols + r_conf_cols
            columns_sql_segment = ", ".join(all_columns_list)
            placeholders_sql_segment = ", ".join(["%s"] * len(all_columns_list))

            sql = f"""
                INSERT INTO user_travel_data (usercode, {columns_sql_segment}) 
                VALUES (%s, {placeholders_sql_segment})
            """

            values_for_tourist_sites = tourist_sites_ids_from_form[:count]
            values_for_missions = missions[:count]
            initial_mission_confirmed_values = [0] * count
            initial_site_confirmed_values = ([2] + [0] * (count - 1)) if count > 0 else []
            initial_route_confirmed_values = [0] * (count - 1) if count > 1 else []

            params = ([usercode] +
                      values_for_tourist_sites +
                      values_for_missions +
                      initial_mission_confirmed_values +
                      initial_site_confirmed_values +
                      initial_route_confirmed_values)

            if len(params) != (1 + len(all_columns_list)):
                print("CRITICAL DEBUG: 파라미터 개수 불일치!")
                return "서버 내부 오류: 파라미터 개수 불일치.", 500

            cursor.execute(sql, params)
            db_conn_insert.commit()

    except pymysql.MySQLError as e_db_insert:
        print(f"데이터베이스 삽입 오류: {e_db_insert}")
        if db_conn_insert and db_conn_insert.open: db_conn_insert.rollback()
        return "오류 발생 (DB 삽입 실패)!", 500
    except Exception as e_insert:
        print(f"일반 삽입 오류: {e_insert}")
        if db_conn_insert and db_conn_insert.open: db_conn_insert.rollback()
        return "오류 발생 (삽입 실패)!", 500
    finally:
        if db_conn_insert and db_conn_insert.open:
            db_conn_insert.close()

    return redirect(url_for('live_with_usercode', usercode=usercode, count=count))


@app.route('/live/<usercode>', methods=['GET'])
def live_with_usercode(usercode):
    count = int(request.args.get('count', 0))
    connection = None
    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            if count == 0:
                return "선택된 관광지가 없습니다. (count=0)", 400

            site_columns = [f'tourist_site_{i}' for i in range(1, count + 1)]
            mission_columns = [f'mission_{i}' for i in range(1, count + 1)]
            mission_confirmed_columns = [f'mission_{i}_confirmed' for i in range(1, count + 1)]
            site_status_columns = [f'tourist_site_{i}_confirmed' for i in range(1, count + 1)]

            route_columns = []
            if count > 1:
                route_columns = [f'route_{i}_confirmed' for i in range(1, count)]

            all_columns = site_columns + mission_columns + mission_confirmed_columns + site_status_columns + route_columns

            sql = f"""
                SELECT {', '.join(all_columns)}
                FROM user_travel_data 
                WHERE usercode = %s
            """
            cursor.execute(sql, (usercode,))
            user_data = cursor.fetchone()

            if not user_data:
                return "잘못된 사용자 코드입니다.", 404

            tourist_sites = []
            for i in range(1, count + 1):
                site_id = user_data.get(f'tourist_site_{i}')
                if site_id:
                    sql_site = "SELECT id, name, address, mapx, mapy, image FROM tourist_attraction WHERE id = %s"
                    cursor.execute(sql_site, (site_id,))
                    site_info = cursor.fetchone()
                    if site_info:
                        tourist_sites.append(site_info)
                    else:
                        tourist_sites.append(None)
                else:
                    tourist_sites.append(None)

            markers = []
            statuses = []
            for i, site in enumerate(tourist_sites):
                if site:
                    status = user_data.get(f'tourist_site_{i + 1}_confirmed', 0)
                    markers.append({
                        'name': site['name'],
                        'mapx': float(site['mapx']) if site.get('mapx') else 0.0,
                        'mapy': float(site['mapy']) if site.get('mapy') else 0.0,
                        'status': status,
                        'site_number': i + 1
                    })
                    statuses.append(status)
                else:
                    statuses.append(None)

            routes = []
            if count > 1:
                for i in range(1, count):
                    route_status = user_data.get(f'route_{i}_confirmed', 0)
                    routes.append({
                        'status': route_status,
                        'route_number': i
                    })

            missions_live = [user_data.get(f'mission_{i}') for i in range(1, count + 1)]
            mission_statuses_live = [user_data.get(f'mission_{i}_confirmed', 0) for i in
                                     range(1, count + 1)]  # Pass raw status

        valid_sites_count = len([s for s in tourist_sites if s is not None])

        return render_template(
            'live.html',
            usercode=usercode,
            tourist_sites=tourist_sites,
            missions=missions_live,
            mission_statuses=mission_statuses_live,  # Pass numeric statuses
            markers=markers,
            statuses=statuses,
            routes=routes,
            count=valid_sites_count
        )
    except Exception as e:
        print(f"오류 발생 (live_with_usercode): {e}")
        return "오류 발생!", 500
    finally:
        if connection and connection.open:
            connection.close()


@app.route('/mission')
def mission_page():
    usercode = request.args.get('usercode')
    return render_template('mission.html', usercode=usercode)


@app.route('/get_mission_details/<usercode>', methods=['GET'])
def get_mission_details(usercode):
    connection = None
    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            sql = """
                SELECT
                    mission_1, mission_1_confirmed, tourist_site_1, tourist_site_1_confirmed,
                    mission_2, mission_2_confirmed, tourist_site_2, tourist_site_2_confirmed,
                    mission_3, mission_3_confirmed, tourist_site_3, tourist_site_3_confirmed
                FROM user_travel_data
                WHERE usercode = %s
            """
            cursor.execute(sql, (usercode,))
            user_data = cursor.fetchone()

            if not user_data:
                return jsonify({"success": False, "error": "사용자 데이터를 찾을 수 없습니다."}), 404

            missions_data = []
            for i in range(1, 4):
                mission_id_key = f'mission_{i}'
                mission_confirmed_key = f'mission_{i}_confirmed'
                tourist_site_id_key = f'tourist_site_{i}'
                tourist_site_status_key = f'tourist_site_{i}_confirmed'

                mission_id = user_data.get(mission_id_key)
                mission_confirmed_status_val = user_data.get(mission_confirmed_key)  # Raw value (0, 1, 3, or None)
                tourist_site_id = user_data.get(tourist_site_id_key)
                current_tourist_site_status = user_data.get(tourist_site_status_key)

                site_info_to_add = {
                    "site_name": "정보 없음",
                    "site_image": None
                }

                if tourist_site_id:
                    cursor.execute("SELECT name, image FROM tourist_attraction WHERE id = %s", (tourist_site_id,))
                    site_details = cursor.fetchone()
                    if site_details:
                        site_info_to_add["site_name"] = site_details['name']
                        site_info_to_add["site_image"] = site_details['image']

                if mission_id:
                    cursor.execute("SELECT id, title, content FROM mission WHERE id = %s", (mission_id,))
                    mission_info = cursor.fetchone()

                    if mission_info:
                        missions_data.append({
                            "id": mission_info['id'],
                            "title": mission_info['title'],
                            "content": mission_info['content'],
                            "confirmed_status": mission_confirmed_status_val if mission_confirmed_status_val is not None else 0,
                            "mission_number": i,
                            "site_name": site_info_to_add["site_name"],
                            "site_image": site_info_to_add["site_image"],
                            "tourist_site_status": current_tourist_site_status if current_tourist_site_status is not None else 0
                        })
                    else:
                        missions_data.append({
                            "id": None,
                            "title": "미션 정보를 찾을 수 없습니다.",
                            "content": "",
                            "confirmed_status": mission_confirmed_status_val if mission_confirmed_status_val is not None else 0,
                            "mission_number": i,
                            "site_name": site_info_to_add["site_name"],
                            "site_image": site_info_to_add["site_image"],
                            "tourist_site_status": current_tourist_site_status if current_tourist_site_status is not None else 0
                        })
                elif tourist_site_id:
                    missions_data.append(None)  # 유지: 미션은 없지만 슬롯은 존재할 수 있음
                else:
                    missions_data.append(None)
            return jsonify({"success": True, "missions": missions_data})
    except Exception as e:
        print(f"사용자 코드 {usercode}에 대한 미션 상세 정보 가져오기 오류: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if connection and connection.open:
            connection.close()


@app.route('/update_mission_status', methods=['POST'])
def update_mission_status():
    data = request.get_json()
    usercode = data.get('usercode')
    mission_number = data.get('mission_number')
    new_status = data.get('new_status')  # Changed from 'confirmed' to 'new_status'

    if not all([usercode, mission_number is not None, new_status is not None]):
        return jsonify({"success": False, "error": "필수 파라미터가 누락되었습니다."}), 400

    if not isinstance(mission_number, int) or not (1 <= mission_number <= 3):  # Assuming max 3 missions
        return jsonify({"success": False, "error": "잘못된 mission_number 값입니다."}), 400

    if not isinstance(new_status, int) or new_status not in [0, 1, 3]:  # Allowed statuses
        return jsonify({"success": False, "error": "잘못된 new_status 값입니다. 0, 1, 또는 3이어야 합니다."}), 400

    confirmed_value = new_status  # Use new_status directly
    mission_confirmed_column = f'mission_{mission_number}_confirmed'
    connection = None
    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            sql = f"UPDATE user_travel_data SET {mission_confirmed_column} = %s WHERE usercode = %s"
            cursor.execute(sql, (confirmed_value, usercode))
            connection.commit()

            if cursor.rowcount > 0:
                return jsonify({"success": True, "message": "미션 상태가 업데이트되었습니다."})
            else:
                cursor.execute("SELECT 1 FROM user_travel_data WHERE usercode = %s", (usercode,))
                if not cursor.fetchone():
                    return jsonify({"success": False, "error": "해당 usercode를 찾을 수 없습니다."}), 404
                return jsonify(
                    {"success": True, "message": "미션 상태가 이미 해당 값으로 설정되어 있거나 변경 사항이 없습니다."})
    except pymysql.MySQLError as e:
        print(f"DB 오류 (미션 상태 업데이트): {e}")
        if connection and connection.open: connection.rollback()
        return jsonify({"success": False, "error": f"데이터베이스 오류: {str(e)}"}), 500
    except Exception as e:
        print(f"미션 상태 업데이트 중 일반 오류: {e}")
        if connection and connection.open: connection.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if connection and connection.open:
            connection.close()


@app.route('/update_status', methods=['POST'])
def update_status():
    data = request.get_json()
    usercode = data.get('usercode')
    site_number = data.get('site_number')
    new_status = data.get('new_status')

    if not all([usercode, site_number, new_status is not None]):
        return jsonify({'status': 'error', 'message': '필수 파라미터 누락'}), 400

    connection = None
    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            sql = f"UPDATE user_travel_data SET tourist_site_{site_number}_confirmed = %s WHERE usercode = %s"
            cursor.execute(sql, (new_status, usercode))
            connection.commit()
            if cursor.rowcount > 0:
                return jsonify({'status': 'success'})
            else:
                return jsonify({'status': 'error', 'message': '업데이트할 데이터가 없거나 usercode를 찾을 수 없습니다.'}), 404

    except pymysql.MySQLError as e:
        print(f"DB error: {e}")
        if connection and connection.open: connection.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    except Exception as e:
        print(f"Error: {e}")
        if connection and connection.open: connection.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if connection and connection.open:
            connection.close()


@app.route('/update_cancel', methods=['POST'])
def update_cancel():
    data = request.json
    usercode = data.get('usercode')
    item_type = data.get('item_type')
    item_number_str = data.get('item_number')

    if not all([usercode, item_type, item_number_str]):
        return jsonify({'status': 'error', 'message': '필수 파라미터 누락'}), 400

    try:
        item_number = int(item_number_str)
    except ValueError:
        return jsonify({'status': 'error', 'message': 'item_number는 정수여야 합니다.'}), 400

    status_sequence = [
        'tourist_site_1_confirmed',
        'route_1_confirmed',
        'tourist_site_2_confirmed',
        'route_2_confirmed',
        'tourist_site_3_confirmed'
    ]
    connection = None
    cursor = None
    try:
        connection = pymysql.connect(**db_config)
        cursor = connection.cursor()

        current_index = -1
        max_site_num = 0
        max_route_num = 0
        for s in status_sequence:
            if "tourist_site_" in s:
                num = int(s.split("_")[2])
                if num > max_site_num: max_site_num = num
            elif "route_" in s:
                num = int(s.split("_")[1])
                if num > max_route_num: max_route_num = num

        if item_type == 'site' and not (1 <= item_number <= max_site_num):
            return jsonify({'status': 'error', 'message': f'잘못된 site_number: {item_number}'}), 400
        if item_type == 'route' and not (1 <= item_number <= max_route_num):
            return jsonify({'status': 'error', 'message': f'잘못된 route_number: {item_number}'}), 400

        for i, status_col_name in enumerate(status_sequence):
            if item_type == 'site' and status_col_name.startswith(f'tourist_site_{item_number}_confirmed'):
                current_index = i
                break
            elif item_type == 'route' and status_col_name.startswith(f'route_{item_number}_confirmed'):
                current_index = i
                break

        if current_index == -1:
            return jsonify({'status': 'error', 'message': '취소할 항목을 찾을 수 없습니다.'}), 404

        updates = []
        for i, status_col_name_update in enumerate(status_sequence):
            if i == current_index:
                updates.append(f"{status_col_name_update} = 2")
            elif i > current_index:
                updates.append(f"{status_col_name_update} = 0")

        if updates:
            sql = f"""UPDATE user_travel_data 
                     SET {', '.join(updates)}
                     WHERE usercode = %s"""
            cursor.execute(sql, (usercode,))
            connection.commit()
            if cursor.rowcount > 0:
                return jsonify({'status': 'success'})
            else:
                return jsonify({'status': 'error', 'message': '업데이트할 데이터가 없거나 usercode를 찾을 수 없습니다.'}), 404
        else:
            return jsonify({'status': 'success', 'message': '변경할 후속 상태가 없습니다.'})

    except Exception as e:
        print(f"Error in update_cancel: {e}")
        if connection and connection.open: connection.rollback()
        return jsonify({'status': 'error', 'message': str(e)})

    finally:
        if cursor:
            cursor.close()
        if connection and connection.open:
            connection.close()


@app.route('/update_route_status', methods=['POST'])
def update_route_status():
    data = request.get_json()
    usercode = data.get('usercode')
    route_number = data.get('route_number')
    new_status = data.get('new_status')

    if not all([usercode, route_number, new_status is not None]):
        return jsonify({'status': 'error', 'message': '필수 파라미터 누락'}), 400

    connection = None
    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            sql = f"UPDATE user_travel_data SET route_{route_number}_confirmed = %s WHERE usercode = %s"
            cursor.execute(sql, (new_status, usercode))
            connection.commit()

            if cursor.rowcount > 0:
                return jsonify({'status': 'success'})
            else:
                return jsonify({'status': 'error', 'message': '업데이트할 데이터가 없거나 usercode를 찾을 수 없습니다.'}), 404

    except pymysql.MySQLError as e:
        print(f"DB error: {e}")
        if connection and connection.open: connection.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    except Exception as e:
        print(f"Error: {e}")
        if connection and connection.open: connection.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if connection and connection.open:
            connection.close()


@app.route('/review/<usercode>')
def review_page(usercode):
    connection = None
    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT * FROM user_travel_data WHERE usercode = %s", (usercode,))
            user_data = cursor.fetchone()

            if not user_data:
                return "여행 데이터가 존재하지 않습니다.", 404

            selected_site_ids = []
            for i in range(1, 4):
                site_key = f'tourist_site_{i}'
                if site_key in user_data and user_data[site_key]:
                    selected_site_ids.append(user_data[site_key])

        sites_to_review = []
        if selected_site_ids:
            for site_id in selected_site_ids:
                site_details = get_site_details_by_id(site_id)
                if site_details:
                    sites_to_review.append(site_details)

        return render_template('review.html', usercode=usercode, sites_to_review=sites_to_review)

    except Exception as e:
        print(f"Error in review_page for usercode {usercode}: {e}")
        return "후기 페이지를 불러오는 중 오류가 발생했습니다.", 500
    finally:
        if connection and connection.open:
            connection.close()


@app.route('/submit_review', methods=['POST'])
def submit_review():
    usercode = request.form.get('usercode')
    MAX_REVIEW_LENGTH = 300
    connection = None  # Define connection here to ensure it's available in finally
    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            for key, value in request.form.items():
                if key.startswith('review_text_'):
                    site_id = key.replace('review_text_', '')
                    review_content = value

                    if review_content and len(review_content) > MAX_REVIEW_LENGTH:
                        review_content = review_content[:MAX_REVIEW_LENGTH]
                        print(f"Warning: Review for site {site_id} truncated to {MAX_REVIEW_LENGTH} characters.",
                              file=sys.stderr)

                    rating_str = request.form.get(f'rating_{site_id}')
                    rating_value = 3

                    if rating_str:
                        try:
                            int_val = int(rating_str)
                            if 1 <= int_val <= 5:
                                rating_value = int_val
                        except ValueError:
                            pass

                    if site_id and (review_content or rating_value is not None):
                        sql = """
                           INSERT INTO review (tourist_attraction_id, content, rating)
                           VALUES (%s, %s, %s)
                           """
                        cursor.execute(sql, (site_id, review_content, rating_value))
            connection.commit()

        return redirect(url_for('finished'))

    except Exception as e:
        print(f"Error submitting review for usercode {usercode}: {e}", file=sys.stderr)
        if connection and connection.open:  # Check if connection was successfully opened
            connection.rollback()
        return "후기를 제출하는 중 오류가 발생했습니다.", 500
    finally:
        if connection and connection.open:
            connection.close()


@app.route('/finished')
def finished():
    return render_template('finished.html')


@app.route('/imformation_panel/<string:site_name>', methods=['GET'])
def imformation_panel(site_name):
    from urllib.parse import unquote
    site_name = unquote(site_name)
    # print(f"DEBUG: Received site_name for panel: {site_name}")
    
    connection = None
    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            sql_tourist = "SELECT * FROM tourist_attraction WHERE name = %s"
            cursor.execute(sql_tourist, (site_name,))
            tourist_info = cursor.fetchone()
            if not tourist_info:
                return "관광지 정보를 찾을 수 없습니다.", 404

            sql_review_count = "SELECT COUNT(*) AS review_count FROM review WHERE tourist_attraction_id = %s"
            cursor.execute(sql_review_count, (tourist_info['id'],))
            review_count_result = cursor.fetchone()
            review_count = review_count_result['review_count'] if review_count_result else 0

            sql_reviews = "SELECT * FROM review WHERE tourist_attraction_id = %s"
            cursor.execute(sql_reviews, (tourist_info['id'],))
            reviews = cursor.fetchall() if cursor.rowcount > 0 else []

            average_rating = None
            if reviews:
                average_rating = sum(review['rating'] for review in reviews) / len(reviews)

        return render_template(
            'imformation_2.html',
            tourist_info=tourist_info,
            review_count=review_count,
            reviews=reviews,
            average_rating=average_rating
        )
    except Exception as e:
        import traceback
        print(f"Error in imformation_panel: {e}")
        traceback.print_exc()
        return "오류 발생", 500
    finally:
        if connection and connection.open:
            connection.close()


@app.route('/imformation_live/<string:site_name>/<string:site_name2>', methods=['GET'])
def imformation(site_name, site_name2=None):
    site_name = unquote(site_name)  # 현재 관광지 이름 디코딩
    site_name2 = unquote(site_name2) if site_name2 != 'NULL' else None  # 이전 관광지 이름 디코딩 (NULL 처리)
    print(f"DEBUG: Received site_name: {site_name}, site_name2: {site_name2}")  # 디버깅 출력

    connection = None
    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            # 현재 관광지 정보 가져오기
            sql_tourist = """
                SELECT * 
                FROM tourist_attraction 
                WHERE name = %s
            """
            cursor.execute(sql_tourist, (site_name,))
            tourist_info = cursor.fetchone()

            if not tourist_info:
                # print(f"DEBUG: No tourist attraction found for site_name: {site_name}")
                return "현재 관광지 정보를 찾을 수 없습니다.", 404

            # 리뷰 개수 조회
            sql_review_count = """
                SELECT COUNT(*) AS review_count
                FROM review
                WHERE tourist_attraction_id = %s
            """
            cursor.execute(sql_review_count, (tourist_info['id'],))
            review_count_result = cursor.fetchone()
            review_count = review_count_result['review_count'] if review_count_result else 0

            # 리뷰 조회
            sql_reviews = """
                SELECT *
                FROM review
                WHERE tourist_attraction_id = %s
            """
            cursor.execute(sql_reviews, (tourist_info['id'],))
            reviews = cursor.fetchall() if cursor.rowcount > 0 else []

            # 평점 평균 계산
            average_rating = None
            if reviews:
                average_rating = sum(review['rating'] for review in reviews) / len(reviews)

            # 이전 관광지 정보 가져오기 (site_name2가 있을 경우)
            tourist_info2 = None
            if site_name2:
                cursor.execute(sql_tourist, (site_name2,))
                tourist_info2 = cursor.fetchone()

        # 템플릿 렌더링 전에 데이터 출력
        # print(f"DEBUG: Tourist Info: {tourist_info}")
        # print(f"DEBUG: Tourist Info2: {tourist_info2}")
        # print(f"DEBUG: Review Count: {review_count}")
        # print(f"DEBUG: Average Rating: {average_rating}")
        # print(f"DEBUG: Reviews: {reviews}")

        return render_template(
            'imformation_live.html',
            tourist_info=tourist_info,
            tourist_info2=tourist_info2,
            review_count=review_count,
            reviews=reviews,
            average_rating=average_rating
        )
    except Exception as e:
        import traceback
        print(f"Error in imformation route: {e}")
        traceback.print_exc()
        return "오류가 발생했습니다.", 500
    finally:
        if connection and connection.open:
            connection.close()

def get_site_details_by_id(site_id):
    connection = None
    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            sql = "SELECT id, name, category, image, address FROM tourist_attraction WHERE id = %s"
            cursor.execute(sql, (site_id,))
            return cursor.fetchone()
    except Exception as e:
        print(f"Error fetching site details for {site_id}: {e}")
        return None
    finally:
        if connection and connection.open:
            connection.close()

@app.route('/.well-known/pki-validation/<path:filename>')
def serve_zerossl_challenge(filename):
    return send_from_directory(os.path.join(app.root_path, '.well-known', 'pki-validation'), filename)

if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=443,
        ssl_context=(
            'fullchain.pem',   # 또는 'C:/Users/너의경로/fullchain.pem'
            'private.key'      # 또는 'C:/Users/너의경로/private.key'
        ),
        debug=True
    )