import requests
import pandas as pd
import pprint
from . import tourist_attraction  # 같은 디렉터리에서 tourist_attraction 모듈 가져오기
from . import food_location  # 같은 디렉터리에서 food_location 모듈 가져오기

def get_results():
    # tourist_attraction 모듈에서 관광지 데이터 가져오기
    tourist_sites = tourist_attraction.get_tourist_sites()

    # food_location 모듈에서 음식 장소 데이터 가져오기
    food_locations_cheongju = food_location.get_Cheongju()
    food_locations_chungju = food_location.get_Chungju()

    # 데이터를 사전 형태로 반환
    return {
        "tourist_sites": tourist_sites,
        "food_locations_cheongju": food_locations_cheongju,
        "food_locations_chungju": food_locations_chungju
    }

