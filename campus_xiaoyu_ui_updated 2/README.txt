厦了么鱼｜嘉庚风格界面修正版

本包包含 Streamlit 程序、样式、依赖清单和本地图片素材。不含数据库、.env、邮箱密码或其他密钥。

Mac 更新步骤
1. 在 Finder 中解压 xialemeyu_jiageng_fixed.zip。
2. 打开解压得到的 campus_xiaoyu_ui_updated 2 文件夹，把 app.py、styles.css、requirements.txt 和 assets 文件夹复制到原项目文件夹：
   /Users/xuhaoqingdemac/Downloads/campus_xiaoyu_ui_updated 2
3. 遇到同名文件时选择替换。保留原项目中的 campus_market.db、.env、.streamlit/secrets.toml 和 .venv，不要删除或覆盖这些内容。
4. 切回运行项目的「终端」窗口，按 Control + C 停止旧网站，然后执行：
   cd "/Users/xuhaoqingdemac/Downloads/campus_xiaoyu_ui_updated 2"
   source .venv/bin/activate
   python -m streamlit run app.py
5. 浏览器访问 http://localhost:8501。

若项目还没有 .venv，先在项目目录运行：
   python3 -m venv .venv
   source .venv/bin/activate
   python -m pip install -r requirements.txt

素材与功能说明
- 楼宇背景和教材、电脑、台灯、背包缩略图从你提供的效果图中裁切；运动户外使用随包的原创分类插画。
- 原数据库没有商品图片字段，所以分类缩略图是卡片封面，不代表某条商品的实拍照片。商品仍显示数据库中的名称、分类、价格、发布者和描述。
- 学校邮箱验证码、商品发布、分类筛选、搜索以及 SQLite/PostgreSQL 数据库访问沿用原项目逻辑。实际邮件发送仍需原有 SMTP 配置；没有 SMTP 时保留开发演示验证码模式。
