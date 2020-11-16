import os
from flask import Flask, render_template, request, abort, jsonify

from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import TemplateSendMessage
from linebot.models import (
    ImagemapSendMessage, TextSendMessage, ImageSendMessage, LocationSendMessage, FlexSendMessage, VideoSendMessage,
    URITemplateAction
, MessageEvent, TextMessage, RichMenu, PostbackEvent, AudioSendMessage, StickerSendMessage, PostbackTemplateAction

)
from urllib.parse import parse_qs
from linebot.models.events import FollowEvent
from linebot.models.template import *
import configparser
import json
import requests
import time
import pymysql
from view_form import UserForm
from flask_bootstrap import Bootstrap
import jinja2

from flask_sqlalchemy import SQLAlchemy  # 導入Flask 連線SQL套件

'''
LINE 聊天機器人的基本資料
'''
# 初始化Flask
app = Flask(__name__, static_url_path="/material", static_folder="./material/")
'''
Bootstrap是由Twitter推出的一個用於前端開發的開源工具包，給予HTML、CSS、JavaScriot，提供簡潔、直觀、強悍的前端開發框架，是目前最受環境的前端框架
'''
Bootstrap(app)

config = configparser.ConfigParser()
config.read('config.ini')
line_bot_api = LineBotApi(config.get('line-bot', 'channel_access_token'))
handler = WebhookHandler(config.get('line-bot', 'channel_secret'))
self_user_id = config.get('line-bot', 'self_user_id')
server_url = config.get('line-bot', 'server_url')

'''
取得啟動文件資料夾路徑
os.path.abspath 返回絕對路徑
os.path.dirname 去掉檔名
'''
basedir = os.path.abspath(os.path.dirname(__file__))
'''
設定Flask 連線SQL
'''
user=config.get('EC2','user')
password=config.get('EC2','password')
IP=config.get('EC2','IP')
DBname=config.get('EC2','DBname')

db = SQLAlchemy()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # 設定監控修改
app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{user}:{password}@{IP}/{DBname}"
# app.config['SQLALCHEMY_DATABASE_URI'] = "mysql+pymysql://root:eb103@13.230.68.76:3306/line_bot_db" #設定 app.config['SQLALCHEMY_DATABASE_URI'] = "mysql+pymysql://user_name:password@IP:3306/db_name"
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
db.init_app(app)
app.config['SECRET_KEY'] = '123'
'''
設定測試網站
'''


@app.route('/user', methods=['GET', 'POST'])
def user():
    form = UserForm()
    # flask_wtf類中提供判斷是否表單提交雇來的method, 不需要自行利用request.method來做判斷
    if form.validate_on_submit():
        return 'Success Submit'
    # 如果不是提交過的表單,就是GET,這時候就用回傳user.html網頁
    return render_template('user1.html', form=form)


@app.route('/register', methods=['GET', 'POST'])
def register():
    from model import UserReister
    from form import FormRegister

    form = FormRegister()
    if form.validate_on_submit():
        user = UserReister(
            username=form.username.data,
            email=form.email.data,
            password=form.password.data
        )
        db.session.add(user)
        db.session.commit()
        return 'Success Thank You'
    return render_template('register.html', form=form)


'''
設定Flask 網站首頁
'''


@app.route('/')
def home():
    return render_template('test.html')

@app.route('/SQL')
def index():
    sql_cmd = """
           select *
           from eb103.ikea_test
           """
    query_data = db.engine.execute(sql_cmd)
    print(query_data)
    return 'ok'

'''
設定上傳圖片
'''


@app.route('/up_photo', methods=['post'])
def up_photo():
    img = request.files.get('photo')
    # print((img.filename))

    username = request.form.get("name")
    # print(username )
    path = basedir + "/static/photo/"
    # print(type(path))
    file_path = path + img.filename
    img.save(file_path)
    print('上傳照片成功，上傳的使用者是：' + username)
    return render_template('home.html')





'''
接收 LINE 的資訊
啟動server對外接口，使Line能丟消息進來
'''


@app.route("/callback", methods=['POST'])  # POST
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'


# host = 'localhost'
# port = 3306
# user = 'root'
# passwd = 'root'
# db = 'line_bot_db'
'''
設定對應回復型態判斷
'''


def detect_json_array_to_new_message_array(fileName):
    # 開啟檔案，轉成json
    with open(fileName, 'r', encoding="utf-8") as f:
        jsonArray = json.load(f)

    # 解析json
    returnArray = []
    for jsonObject in jsonArray:

        # 讀取其用來判斷的元件
        message_type = jsonObject.get('type')

        # 轉換
        if message_type == 'text':
            returnArray.append(TextSendMessage.new_from_json_dict(jsonObject))
        elif message_type == 'imagemap':
            returnArray.append(ImagemapSendMessage.new_from_json_dict(jsonObject))
        elif message_type == 'template':
            returnArray.append(TemplateSendMessage.new_from_json_dict(jsonObject))
        elif message_type == 'image':
            returnArray.append(ImageSendMessage.new_from_json_dict(jsonObject))
        elif message_type == 'sticker':
            returnArray.append(StickerSendMessage.new_from_json_dict(jsonObject))
        elif message_type == 'audio':
            returnArray.append(AudioSendMessage.new_from_json_dict(jsonObject))
        elif message_type == 'location':
            returnArray.append(LocationSendMessage.new_from_json_dict(jsonObject))
        elif message_type == 'flex':
            returnArray.append(FlexSendMessage.new_from_json_dict(jsonObject))
        elif message_type == 'video':
            returnArray.append(FlexSendMessage.new_from_json_dict(jsonObject))

            # 回傳
    return returnArray


'''
撰寫用戶關注時，我們要處理的商業邏輯

1. 取得用戶個資，並存回伺服器
2. 把先前製作好的自定義菜單，與用戶做綁定
3. 回應用戶，歡迎用的文字消息與圖片消息
告知handler，如果收到FollowEvent，則做下面的方法處理
'''
'''
設定追蹤處理
'''


# 關注事件處理
@handler.add(FollowEvent)
def process_follow_event(event):
    # 讀取並轉換
    result_message_array = []
    replyJsonPath = "material/Follow/reply.json"

    result_message_array = detect_json_array_to_new_message_array(replyJsonPath)

    # 消息發送
    line_bot_api.reply_message(
        event.reply_token,
        result_message_array
    )

    menuJson = json.load(open('./material/rich_menu/rich_menu.json', 'r', encoding='utf-8'))  # 設定圖文選單功能
    lineRichMenuId = line_bot_api.create_rich_menu(rich_menu=RichMenu.new_from_json_dict(menuJson))
    print(lineRichMenuId)
    uploadImageFile = open("./material/rich_menu/rich_menu.jpg", 'rb')  # 設定圖文選單圖片

    setImageResponse = line_bot_api.set_rich_menu_image(lineRichMenuId, 'image/jpeg', uploadImageFile)

    linkResult = line_bot_api.link_rich_menu_to_user(self_user_id, lineRichMenuId)

    # 取出消息內User的資料
    user_profile = line_bot_api.get_profile(event.source.user_id)
    # 將用戶資訊存在檔案內
    # with open("./users.txt", "a") as myfile:
    #     myfile.write(json.dumps(vars(user_profile), sort_keys=True))
    #     myfile.write('\n')
    user_id = str(event.source.user_id)
    print(user_id)
    select_userid = '''

    SELECT userid from line_bot_db.lineuser;
    '''
    print(type(db.engine.execute(select_userid).fetchall()))
    try:
        if user_id not in select_userid:
            sql2 = f'''INSERT INTO line_bot_db.user_linebot_record(userid)
                                VALUES ("{user_id}");'''
            db.engine.execute(sql2)
            sql1 = f'''INSERT INTO  line_bot_db.lineuser(userid)
                    VALUES ("{user_id}");
                        '''
            db.engine.execute(sql1)

    except Exception:
        pass

    # 將菜單綁定在用戶身上

    line_bot_api.link_rich_menu_to_user(user_id, lineRichMenuId)


'''

handler處理文字消息

收到用戶回應的文字消息，
按文字消息內容，往素材資料夾中，找尋以該內容命名的資料夾，讀取裡面的reply.json

轉譯json後，將消息回傳給用戶

'''


# 文字消息處理
@handler.add(MessageEvent, message=TextMessage)
def process_text_message(event):
    event

    # 讀取本地檔案，並轉譯成消息
    # result_message_array =[]
    # replyJsonPath = "material/"+event.message.text+"/reply.json"
    # result_message_array = detect_json_array_to_new_message_array(replyJsonPath)

    # # 發送
    # line_bot_api.reply_message(
    #     event.reply_token,
    #     result_message_array
    # )


''''

handler處理Postback Event

載入功能選單與啟動特殊功能

解析postback的data，並按照data欄位判斷處理

現有三個欄位
menu, folder, tag

若folder欄位有值，則
    讀取其reply.json，轉譯成消息，並發送

若menu欄位有值，則
    讀取其rich_menu_id，並取得用戶id，將用戶與選單綁定
    讀取其reply.json，轉譯成消息，並發送

'''
'''
清除使用者搜尋紀錄
'''


def init_user_profile(id):
    # from_page = 0
    # to_page =4
    sql_cmd = f"""
        DELETE FROM line_bot_db.user_search
        WHERE userid="{id}";
        """
    db.engine.execute(sql_cmd)
    return 'OK'


@handler.add(PostbackEvent)
def process_postback_event(event):
    # print(event)

    query_string_dict = parse_qs(event.postback.data)
    user_id = str(event.source.user_id)
    # print(user_id)
    print(query_string_dict)
    try:
        # user_id=str(event.source.user_id)

        value = query_string_dict.get('tag')[0]
        Field = query_string_dict.get('name')[0]
        print(Field, value)

        sql = f'''


           UPDATE line_bot_db.user_linebot_record 
           SET {Field}="{value}" 
           WHERE userid="{user_id}";

           '''
        db.engine.execute(sql)
    except Exception as a:
        # print(a)
        callback

    # 取得data內的資料
    # data 如果action 有在內的話
    if "action" in query_string_dict:
        if query_string_dict.get('action')[0] == 'init':
            check = init_user_profile(user_id)
            print(check)
        elif query_string_dict.get('action')[0] == 'recommend':
            Produclist = []
            from get_tfidf_recommendation import get_tfidf_recommendation
            try:
                get_user_search = f''' SELECT user_index FROM line_bot_db.user_linebot_record WHERE userid='{user_id}';'''
                index = db.engine.execute(get_user_search).fetchall()[0][0]

                recommedation_list = get_tfidf_recommendation(index)
                #print(recommedation_list)
                for Product_ID in recommedation_list:
                    # print(Product_ID)
                    search_id = f'''SELECT * FROM eb103.ikea_cl_test_f7 WHERE Product_number="{Product_ID}"'''

                    Product = db.engine.execute(search_id).fetchall()
                    d, a = {}, []
                    for rowproxy in Product:
                        for column, value in rowproxy.items():
                            d = {**d, **{column: value}}
                        a.append(d)
                        #print(a[0])



                        Product_number = a[0]['Product_number']
                        Product_imageurl = a[0]['funiture_url']
                        #print(Product_imageurl)
                        Product_title = a[0]['title']
                        Product_summy = a[0]['Product_Information']
                        Product_url = a[0]['url']
                        # print(Product_number)
                        Carouse = \
                            CarouselColumn(
                                thumbnail_image_url=f"{Product_imageurl}",
                                title=f'{Product_title}',
                                text=f'{Product_summy}',
                                actions=[
                                    PostbackTemplateAction(
                                        label='查看商品',
                                        text=f'{Product_url}',
                                        data=f'tag={Product_number}&name=user_index')
                                    # ,URITemplateAction(
                                    #     label='uri1',
                                    #     uri='http://example.com/1'
                                    # )

                                ]
                            )
                        Produclist.append(Carouse)
                        #print(Produclist)
                result_message_array = TemplateSendMessage(
                    alt_text='Carousel template',
                    template=CarouselTemplate(
                        columns=Produclist
                    )
                )

                line_bot_api.reply_message(
                    event.reply_token,
                    result_message_array
                )
            except Exception:
                # 查詢pages值12321
                search_sql = f'''
                                   SELECT * FROM line_bot_db.user_search WHERE userid="{user_id}";
                                   '''
                data_search = db.engine.execute(search_sql).fetchall()
                if data_search == []:
                    # 預設pages 值
                    page = 0
                    insert_sql = f'''
                                        INSERT INTO line_bot_db.user_search(userid,pages)
                                        VALUES ("{user_id}",{page});'''

                    db.engine.execute(insert_sql)

                # 查詢結果如果不為空值 則將結果取出dict
                elif data_search != []:
                    e, c = {}, []
                    for data in data_search:
                        for column, value in data.items():
                            e = {**e, **{column: value}}
                        c.append(e)
                    # 將page 取出放入sql內
                    page = (c[0]['pages'])
                sql=f'''SELECT * FROM eb103.ikea_cl_test_f7
                    ORDER BY rand()
                    LIMIT 4,4'''
                Carouselist = []
                data = (db.engine.execute(sql).fetchall())

                d, a = {}, []
                for rowproxy in data:
                    for column, value in rowproxy.items():
                        d = {**d, **{column: value}}
                    a.append(d)
                for i in a:
                    all = dict(i)
                    # index
                    user_index = all['MyUnknownColumn']
                    # 商品名稱
                    title = all['title']
                    # 商品ID
                    product_number = all['Product_number']
                    print(product_number)
                    # 商品種類
                    object_type = all['category']
                    # 商品介紹
                    Product_summy = all['Product_Information']
                    # fileall = '商品介紹: ' + product_number + summary + object_type
                    # 商品連結
                    url = all['url']

                    # 商品價格
                    price = all['price']
                    # 商品照片
                    images = all['funiture_url']

                    # object_string = object_string.replace("[", "").replace("]", "").replace("'", "")
                    # object_string = object_string.split(',')
                    #
                    # print(object_string)

                    Carouse = \
                        CarouselColumn(
                            thumbnail_image_url=images,
                            title=f'{title}',
                            text=f'{Product_summy}',
                            actions=[
                                PostbackTemplateAction(
                                    label='查看商品',
                                    text=f'{url}',
                                    data=f'tag={product_number}&name=user_index')
                                # ,URITemplateAction(
                                #     label='uri1',
                                #     uri='http://example.com/1'
                                # )

                            ]
                        )
                    Carouselist.append(Carouse)
                    # 下一頁


                result_message_array = TemplateSendMessage(
                    alt_text='Carousel template',
                    template=CarouselTemplate(
                        columns=Carouselist
                    )
                )

                line_bot_api.reply_message(
                    event.reply_token,
                    result_message_array
                )
        else:
            pass

    if 'folder' in query_string_dict:

        # print(query_string_dict.get('folder'))

        #     if query_string_dict.get('folder')[0]=='Furniture':
        #         # if query_string_dict.get('tag')[0]=='nextpage':
        #         #      sql = f'''
        #         #             SELECT * FROM line_bot_db.csv2 Limit 4,4;
        #         #             '''
        #         # else:
        #         page = 0
        #         search_sql=f'''
        #         SELECT pages from line_bot_db.user_search WHERE userid="{user_id}";
        #         '''
        #         data_search=db.engine.execute(search_sql).fetchall()
        #         if data_search==[]:
        #
        #             insert_sql=f'''
        #                     INSERT INTO line_bot_db.user_search(userid,pages)
        #                     VALUES ("{user_id}",{page});'''
        #
        #
        #             db.engine.execute(insert_sql)
        #
        #
        #         elif data_search !=[]:
        #             e,c ={},[]
        #             for data in data_search:
        #                 for column,value in data.items():
        #                     e={**e,**{column:value}}
        #                 c.append(e)
        #             page=(c[0]['pages'])
        #
        #         sql = f'''
        #                 SELECT * FROM eb103.ikea_test Limit {page},4 ;
        #                 '''
        #         page +=4
        #         UPdate=f'''
        #                 UPDATE user_search
        # 	            SET pages={page}
        #                 WHERE userid="{user_id}";
        #                 '''
        #         db.engine.execute(UPdate)
        #         Carouselist = []
        #         data = (db.engine.execute(sql).fetchall())
        #         d,a={},[]
        #         for rowproxy in data:
        #             for column,value in rowproxy.items():
        #                 d={**d,**{column:value}}
        #             a.append(d)
        #
        #         #print(a[0]['images'][0])
        #         # object_string=dict(a[0])
        #         # print(type(object_string))
        #         # print(object_string['title'])
        #         #str轉list
        #         #object_string=object_string.replace("[", "").replace("]", "").replace("'", "")
        #         #object_string=object_string.split(',')
        #         #print(object_string[0])
        #         #print(type(object_string))
        #         print((a))
        #         for i in a:
        #             all=dict(i)
        #             title =all['title']
        #             product_number=all['Product number']+'\n'
        #             object_type=all['type']+'\n'
        #             summary=all['summary']+'\n'
        #             fileall='商品介紹: '+product_number+summary+object_type
        #             url=all['url']
        #
        #             object_string = all['interior_photo']
        #
        #             # object_string = object_string.replace("[", "").replace("]", "").replace("'", "")
        #             # object_string = object_string.split(',')
        #             #
        #             # print(object_string)
        #
        #             Carouse=\
        #                  CarouselColumn(
        #                      thumbnail_image_url=object_string ,
        #                      title=f'{title}',
        #                      text=f'{fileall}',
        #                      actions=[
        #                          PostbackTemplateAction(
        #                              label='查看商品',
        #                              text=f'{url}',
        #                              data='tag=回傳商品的點擊率'),
        #                          # URITemplateAction(
        #                          #     label='uri1',
        #                          #     uri='http://example.com/1'
        #                          # )
        #
        #
        #                      ]
        #                                 )
        #             Carouselist.append(Carouse)
        #         nextpage=CarouselColumn(
        #                 thumbnail_image_url='https://cdn.stocksnap.io/img-thumbs/960w/autumn-trees_FMKZ57EIMQ.jpg',
        #                 title='都沒有你要的?',
        #                 text='看看下一頁',
        #                 actions=[
        #                 PostbackTemplateAction(
        #                     label='下一頁',
        #                     text='看看商品上架',
        #                     data='folder=Furniture&tag=nextpage'),
        #                 # PostbackTemplateAction(
        #                 #     label='下一頁',
        #                 #     text='看看商品上架',
        #                 #     data='folder=Furniture&tag=nextpage'
        #                 # )
        #                 ]
        #         )
        #         Carouselist.append(nextpage)
        #         result_message_array = TemplateSendMessage(
        #             alt_text='Carousel template',
        #             template=CarouselTemplate(
        #                 columns=Carouselist
        #             )
        #         )
        #
        #
        #
        #     else:
        result_message_array = []

        replyJsonPath = 'material/' + query_string_dict.get('folder')[0] + "/reply.json"
        # print(replyJsonPath) #路徑
        result_message_array = detect_json_array_to_new_message_array(replyJsonPath)
        # print(result_message_array)

        line_bot_api.reply_message(
            event.reply_token,
            result_message_array
        )
    # 如果data 內有end 則輸出輪播商品
    elif 'end' in query_string_dict:
        # user_id = str(event.source.user_id)
        # 取出使用者查詢條件dict
        data_search_sql = f'''
        SELECT * FROM line_bot_db.user_linebot_record WHERE userid="{user_id}";
        '''
        data = (db.engine.execute(data_search_sql).fetchall())
        d, a = {}, []
        for rowproxy in data:
            for column, value in rowproxy.items():
                d = {**d, **{column: value}}
            a.append(d)
        print(a)

        all = dict(a[0])
        style = all['style']
        category = all['category']
        price = all['price']
        colour = all['colour']

        # 查詢pages值
        search_sql = f'''
                    SELECT * FROM line_bot_db.user_search WHERE userid="{user_id}";
                    '''
        data_search = db.engine.execute(search_sql).fetchall()

        # print(data_search)
        # 查詢結果如果是空值 初始化值寫入
        if data_search == []:
            # 預設pages 值
            page = 0
            insert_sql = f'''
                                INSERT INTO line_bot_db.user_search(userid,pages)
                                VALUES ("{user_id}",{page});'''

            db.engine.execute(insert_sql)

        # 查詢結果如果不為空值 則將結果取出dict
        elif data_search != []:
            e, c = {}, []
            for data in data_search:
                for column, value in data.items():
                    e = {**e, **{column: value}}
                c.append(e)
            # 將page 取出放入sql內
            page = (c[0]['pages'])
            # print(page)
        # sql放入指定條件變數
        sql = f'''
                    SELECT * FROM eb103.ikea_cl_test_f7
                    WHERE style="{style}"
                    AND category="{category}"
                    AND (new_color_1 LIKE "%%{colour}%%" OR new_color_1 LIKE "%%{colour}%%" OR new_color_1 LIKE "%%{colour}%%")
                    AND price {price}
                    ORDER BY rand()
                    LIMIT {page},4

                            '''
        print(sql)
        # 每次查詢加4 並更新寫入Mysql
        page += 4
        # print(page)
        UPdate = f'''
                            UPDATE line_bot_db.user_search
                            SET pages={page}
                            WHERE userid="{user_id}";
                            '''
        db.engine.execute(UPdate)
        # 查詢
        Carouselist = []
        data = (db.engine.execute(sql).fetchall())

        d, a = {}, []
        for rowproxy in data:
            for column, value in rowproxy.items():
                d = {**d, **{column: value}}
            a.append(d)

        # print(a[0]['images'][0])
        # object_string=dict(a[0])
        # print(type(object_string))
        # print(object_string['title'])
        # str轉list
        # object_string=object_string.replace("[", "").replace("]", "").replace("'", "")
        # object_string=object_string.split(',')
        # print(object_string[0])
        # print(type(object_string))
        print(a)
        for i in a:
            all = dict(i)
            # index
            user_index = all['MyUnknownColumn']
            # 商品名稱
            title = all['title']
            # 商品ID
            product_number = all['Product_number']
            print(product_number)
            # 商品種類
            object_type = all['category']
            # 商品介紹
            Product_summy = all['Product_Information']
            # fileall = '商品介紹: ' + product_number + summary + object_type
            # 商品連結
            url = all['url']

            # 商品價格
            price = all['price']
            # 商品照片
            images = all['funiture_url']

            # object_string = object_string.replace("[", "").replace("]", "").replace("'", "")
            # object_string = object_string.split(',')
            #
            # print(object_string)

            Carouse = \
                CarouselColumn(
                    thumbnail_image_url=images,
                    title=f'{title}',
                    text=f'{Product_summy}',
                    actions=[
                        PostbackTemplateAction(
                            label='查看商品',
                            text=f'{url}',
                            data=f'tag={product_number}&name=user_index')
                        # ,URITemplateAction(
                        #     label='uri1',
                        #     uri='http://example.com/1'
                        # )

                    ]
                )
            Carouselist.append(Carouse)
        # 下一頁
        nextpage = CarouselColumn(
            thumbnail_image_url='https://cdn.stocksnap.io/img-thumbs/960w/autumn-trees_FMKZ57EIMQ.jpg',
            title='都沒有你要的?',
            text='看看下一頁',
            actions=[
                PostbackTemplateAction(
                    label='下一頁',
                    text='看看商品上架',
                    data='end=nextpage'),
                # PostbackTemplateAction(
                #     label='下一頁',
                #     text='看看商品上架',
                #     data='folder=Furniture&tag=nextpage'
                # )
            ]
        )
        Carouselist.append(nextpage)

        result_message_array = TemplateSendMessage(
            alt_text='Carousel template',
            template=CarouselTemplate(
                columns=Carouselist
            )
        )

        line_bot_api.reply_message(
            event.reply_token,
            result_message_array
        )



    #     linkRichMenuId = open("material/" + query_string_dict.get('menu')[0] + '/rich_menu_id', 'r').read()
    #     line_bot_api.link_rich_menu_to_user(event.source.user_id, linkRichMenuId)
    #
    #     replyJsonPath = 'material/' + query_string_dict.get('menu')[0] + "/reply.json"
    #     result_message_array = detect_json_array_to_new_message_array(replyJsonPath)
    #
    #     line_bot_api.reply_message(
    #         event.reply_token,
    #         result_message_array
    #     )
    # data 型態如果有  information  在 query_string_dict內
    elif 'information' in query_string_dict:  # 使用者資料
        # conn = pymysql.connect(host=host, port=port, user=user, passwd=passwd, db=db)
        # cursor = conn.cursor()
        #
        # 抓取使用者id
        user_profile = line_bot_api.get_profile(event.source.user_id)
        # userID = str(user_profile.user_id)
        print(user_id)
        # init_user_profile(userID)

        try:
            @app.route('/html1/<userID>', methods=['GET'])
            def html2(userID):
                return render_template('surveyweb.html', ID=user_id)

            @app.route('/submit', methods=['POST'])
            def submit():
                user_ID = request.values.get('user_ID')
                name = str(request.values.get('name'))
                email = str(request.values.get('email'))
                gender = int(request.form.get('gender'))
                age = str(request.form.get('age'))

                print(user_ID, name, email, gender, age)
                sql = f'''
                UPDATE line_bot_db.lineuser
                SET self_name="{name}",email="{email}",gender={gender}
                ,age="{age}"
                WHERE userid="{user_ID}"

                '''
                db.engine.execute(sql)
                return '資料更改完成'
        except:
            pass
        # usedb=f'USE line_bot_db;'
        # db.engine.execute(usedb)
        sql = f''' 
        SELECT * FROM line_bot_db.lineuser WHERE userid="{user_id}";

        '''
        try:
            data = list((db.engine.execute(sql).fetchall())[0])

            data1 = '名字:' + data[1] + '\n'
            data2 = '信箱:' + data[2] + '\n'

            if data[3] == '1':
                data[3] = '男'
            else:
                data[3] = '女'
            data3 = '性別:' + data[3] + '\n'

            if data[4] == 'age1':
                data[4] = '未滿20歲'
            elif data[4] == 'age2':
                data[4] = '20~29歲'
            elif data[4] == 'age3':
                data[4] = '30~39歲'
            elif data[4] == 'age4':
                data[4] = '40~49歲'
            elif data[4] == 'age5':
                data[4] = '50歲以上'
            data4 = '年齡:' + data[4] + '\n'

            falldata = data1 + data2 + data3 + data4
            print(falldata)
            message = [TextSendMessage(falldata),
                       TemplateSendMessage(
                           alt_text="confirm template",
                           template=ButtonsTemplate(

                               title='你的基本資料',
                               text='以上為個人資料',
                               actions=[
                                   # PostbackTemplateAction(
                                   #     type="postback",
                                   #     label='看看商品上架',
                                   #     text="看看商品上架-傢俱",
                                   #     data='folder=Furniture'
                                   # ),
                                   URITemplateAction(
                                       label='重新輸入資料',
                                       uri=f"https://{server_url}/html1/{user_id}",

                                   )

                               ]
                           )
                       )
                       ]
        except:
            message = TemplateSendMessage(
                alt_text="confirm template",
                template=ButtonsTemplate(

                    title='你的基本資料',
                    text="尚未輸入資料",
                    actions=[
                        # PostbackTemplateAction(
                        #     type="postback",
                        #     label='看看商品上架',
                        #     text="看看商品上架-傢俱",
                        #     data='folder=Furniture'
                        # ),
                        URITemplateAction(
                            label='輸入資料',
                            uri=f"https://{server_url}/html1/{user_id}",

                        )

                    ]
                )
            )

        line_bot_api.reply_message(
            event.reply_token,
            message)


if __name__ == "__main__":
    app.config['SECRET_KEY'] = 'your key'
    app.run(host='0.0.0.0')
#   app.run(host='0.0.0.0', port=os.environ['PORT'])

