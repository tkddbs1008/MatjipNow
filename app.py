import jwt
import datetime
import hashlib

import requests
from flask import Flask, render_template, jsonify, request, redirect, url_for
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from pymongo import MongoClient
from bs4 import BeautifulSoup

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config['UPLOAD_FOLDER'] = "./static/profile_pics"

SECRET_KEY = 'SPARTA'

client = MongoClient('mongodb+srv://test:sparta@cluster0.07mbu.mongodb.net/Cluster0?retryWrites=true&w=majority')
db = client.dbStore

#------주소 입력받고 좌표값으로 변환-----
# 지도는 localhost:5000으로 접속하셔야 합니다.
headers = {
    "X-NCP-APIGW-API-KEY-ID": "s76fz5795p",
    "X-NCP-APIGW-API-KEY": "slSZ5BKsgMyGfrEp7LFXW8UcaQ7VZpTgW0mMAzHl"
}




all_users = list(db.Store.find({},{'_id':False}))
###Store에서 불러온 주소값으로 xy값을 얻은 후 xy테이블에 Num과 함께 저장###
for i in all_users:
    n = i['Num']
    address = i['Adress']
    r = requests.get(f"https://naveropenapi.apigw.ntruss.com/map-geocode/v2/geocode?query={address}", headers=headers)
    response = r.json()
    if response["status"] == "OK":
        if len(response["addresses"]) > 0:
            x = float(response["addresses"][0]["x"])
            y = float(response["addresses"][0]["y"])
        else:
            print("좌표를 찾지 못했습니다")
    else:
        print(response["status"])
    doc = {'Num':n,'x':x,'y':y}
    db.xy.delete_one({'Num':n})
    db.xy.insert_one(doc)

all_users2 = list(db.xy.find({},{'_id':False}))
for x in all_users2:
    print(x)



@app.route('/')
def home():
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_info = db.users.find_one({"username": payload["id"]})
        return render_template('index.html', user_info=user_info)
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="로그인 시간이 만료되었습니다."))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="로그인 정보가 존재하지 않습니다."))

@app.route('/index', methods=['POST'])
def main_post():
    category = request.form['category']
    local = request.form['local']
    print(category)
    print(local)

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36'}
    data = requests.get(f'https://www.mangoplate.com/search/{local}%20{category}',headers=headers)
    soup = BeautifulSoup(data.text,'html.parser')

    titles = soup.select('body > main > article > div.column-wrapper > div > div > section > div.search-list-restaurants-inner-wrap > ul > li')


    for title in titles:
        store_list = list(db.Store.find({}, {'_id': False}))
        count = len(store_list) + 1
        store_name = title.select_one('div > figure > figcaption > div > a > h2')
        store_name = store_name.text.split('\n')[0]
        store_point = title.select_one('div > figure > figcaption > div > strong').text
        review_point = title.select_one('div > figure > figcaption > div > p.etc_info > span.review_count.ng-binding')
        img_thumnail = title.select_one('div > figure > a > div > img')['data-original'].split(';')[0]

        print(type(store_name))
        print(store_name)
        detail_link = title.select_one('div > figure > a')['href']
        detail_link = 'https://www.mangoplate.com' + detail_link
        # print(detail_link)
        print(img_thumnail)
        print(str(count) + '번째 음식점 이름: ' + store_name + '\n평점:' + store_point)
        data1 = requests.get(detail_link, headers=headers)
        soup1 = BeautifulSoup(data1.text, 'html.parser')
        Address = soup1.select_one(
            'body > main > article > div.column-wrapper > div.column-contents > div > section.restaurant-detail > table > tbody > tr:nth-child(1) > td').text.split(
            '\n')[0]
        PhoneNum = soup1.select_one(
            'body > main > article > div.column-wrapper > div.column-contents > div > section.restaurant-detail > table > tbody > tr:nth-child(2) > td').text
        Food_Category = soup1.select_one(
            'body > main > article > div.column-wrapper > div.column-contents > div > section.restaurant-detail > table > tbody > tr:nth-child(3) > td > span').text
        Parking = soup1.select_one(
            'body > main > article > div.column-wrapper > div.column-contents > div > section.restaurant-detail > table > tbody > tr:nth-child(5) > td').text
        print('주소:' + Address + '\n전화번호: ' + PhoneNum + '\n음식 종류:' + Food_Category + '\n주차 여부:' + Parking)
        #body > main > article > div.column - wrapper > div.column - contents > div > section.restaurant - detail > table > tbody > tr: nth - child(2) > td > span
        print('=============')
        doc = {
            'Num': count,
            'StoreName': store_name,
            'StorePoint': store_point,
            'PhoneNum': PhoneNum,
            'Adress': Address,
            'FoodCategory': Food_Category,
            'Parking': Parking,
            'thumnail': img_thumnail,
            'LocalTag': local,
            'FoodTag': category
        }
        db.Store.insert_one(doc)

    return jsonify({'result':'success','msg':'요청확인'})
@app.route("/index", methods=["GET"])
def store_get():
    store_list = list(db.Store.find({}, {'_id': False}))
    return jsonify({'result': 'success', 'Stores': store_list})

@app.route('/detail')
def detail():
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_info = db.users.find_one({"username": payload["id"]})
        return render_template('detail.html', user_info=user_info)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))

@app.route('/detail/<idNum>')
def store(idNum):
    # 각 상세페이지를 보게 한다
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_info = db.users.find_one({"username": payload["id"]})
        store_info = db.Store.find_one({"Num": idNum}, {"_id": False})
        return render_template('detail.html', user_info=user_info, store_info=store_info)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))

@app.route('/login')
def login():
    msg = request.args.get("msg")
    return render_template('login.html', msg=msg)


@app.route('/user/<username>')
def user(username):
    # 각 사용자의 프로필과 글을 모아볼 수 있는 공간
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        status = (username == payload["id"])  # 내 프로필이면 True, 다른 사람 프로필 페이지면 False
        # 사용자 프로필에 자기글만 볼일수 있게 한번 해보자


        user_info = db.users.find_one({"username": username}, {"_id": False})
        return render_template('user.html', user_info=user_info, status=status)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))


@app.route('/sign_in', methods=['POST'])
def sign_in():
    # 로그인
    username_receive = request.form['username_give']
    password_receive = request.form['password_give']

    pw_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()
    result = db.users.find_one({'username': username_receive, 'password': pw_hash})

    if result is not None:
        payload = {
         'id': username_receive,
         'exp': datetime.utcnow() + timedelta(seconds=60 * 60 * 24)  # 로그인 24시간 유지
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')

        return jsonify({'result': 'success', 'token': token})
    # 찾지 못하면
    else:
        return jsonify({'result': 'fail', 'msg': '아이디/비밀번호가 일치하지 않습니다.'})


@app.route('/sign_up/save', methods=['POST'])
def sign_up():
    username_receive = request.form['username_give']
    password_receive = request.form['password_give']
    password_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()
    doc = {
        "username": username_receive,                               # 아이디
        "password": password_hash,                                  # 비밀번호
        "profile_name": username_receive,                           # 프로필 이름 기본값은 아이디
        "profile_pic": "",                                          # 프로필 사진 파일 이름
        "profile_pic_real": "profile_pics/profile_placeholder.png", # 프로필 사진 기본 이미지
        "profile_info": ""                                          # 프로필 한 마디
    }
    db.users.insert_one(doc)
    return jsonify({'result': 'success'})


@app.route('/sign_up/check_dup', methods=['POST'])
def check_dup():
    username_receive = request.form['username_give']
    exists = bool(db.users.find_one({"username": username_receive}))
    return jsonify({'result': 'success', 'exists': exists})

@app.route('/update_profile', methods=['POST'])
def save_img():
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        username = payload["id"]
        name_receive = request.form["name_give"]
        about_receive = request.form["about_give"]
        new_doc = {
            "profile_name": name_receive,
            "profile_info": about_receive
        }
        if 'file_give' in request.files:
            file = request.files["file_give"]
            filename = secure_filename(file.filename)
            extension = filename.split(".")[-1]
            file_path = f"profile_pics/{username}.{extension}"
            file.save("./static/"+file_path)
            new_doc["profile_pic"] = filename
            new_doc["profile_pic_real"] = file_path
        db.users.update_one({'username': payload['id']}, {'$set':new_doc})
        return jsonify({"result": "success", 'msg': '프로필을 업데이트했습니다.'})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))

# 업데이트 포스팅을 한번 구현해 보자
@app.route('/update_posting', methods=['POST'])
def update_posting():
    token_receive = request.cookies.get('mytoken')
    # try:



@app.route('/posting', methods=['POST'])
def posting():
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_info = db.users.find_one({"username": payload["id"]})
        comment_receive = request.form["comment_give"]
        date_receive = request.form["date_give"]
        num_receive = request.form["num_give"]
        doc = {
            "username": user_info["username"],
            "profile_name": user_info["profile_name"],
            "profile_pic_real": user_info["profile_pic_real"],
            "comment": comment_receive,
            "date": date_receive,
            "Id": num_receive
        }
        db.posts.insert_one(doc)
        return jsonify({"result": "success", 'msg': '포스팅 성공'})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))


@app.route("/get_posts", methods=['GET'])
def get_posts():
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        posts = list(db.posts.find({}).sort("date", -1).limit(20))
        for post in posts:
            post["_id"] = str(post["_id"])
            post["count_heart"] = db.likes.count_documents({"post_id": post["_id"], "type": "heart"})
            post["heart_by_me"] = bool(db.likes.find_one({"post_id": post["_id"], "type": "heart", "username": payload['id']}))
        return jsonify({"result": "success", "msg": "포스팅을 가져왔습니다.", "posts": posts})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))


@app.route('/update_like', methods=['POST'])
def update_like():
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_info = db.users.find_one({"username": payload["id"]})
        post_id_receive = request.form["post_id_give"]
        type_receive = request.form["type_give"]
        action_receive = request.form["action_give"]
        doc = {
            "post_id": post_id_receive,
            "username": user_info["username"],
            "type": type_receive
        }
        if action_receive == "like":
            db.likes.insert_one(doc)
        else:
            db.likes.delete_one(doc)
        count = db.likes.count_documents({"post_id": post_id_receive, "type": type_receive})
        return jsonify({"result": "success", 'msg': 'updated', "count": count})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))


if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)