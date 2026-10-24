# 校园邮箱验证配置

## 本地演示

1. 安装依赖：`pip install -r requirements.txt`
2. 复制 `.env.example` 为 `.env`，保留 `EMAIL_VERIFY_MODE=dev`。
3. 启动 Streamlit：`streamlit run app.py`
4. 展开“学生邮箱验证”，使用 `@xmu.edu.my` 地址申请验证码。页面会显示演示码；输入后可完成当前浏览器会话的验证。

开发模式不会发送邮件，也不能证明用户拥有该邮箱。不要把它当作真实身份验证。

## SMTP 邮件测试

1. 登录 QQ 邮箱网页版，打开“设置 → 账户”，启用 SMTP 服务并生成邮箱授权码。
2. 把 `.env.example` 复制为 `.env`。将 `SMTP_USER` 和 `SMTP_FROM` 改成你的 QQ 邮箱地址，将 `SMTP_PASSWORD` 改成刚生成的授权码，并将 `EMAIL_VERIFY_MODE` 改为 `smtp`。
3. QQ 邮箱配置为 `SMTP_HOST=smtp.qq.com`、`SMTP_PORT=465`、`SMTP_USE_SSL=true`。授权码不是 QQ 登录密码。
4. 启动应用，申请自己的学校邮箱验证码，确认邮件能收到并完成验证。

`.env` 已加入忽略清单，不要提交或分享包含真实凭据的文件。QQ 邮箱 SMTP 需要使用授权码，不要使用 QQ 登录密码。[QQ 邮箱授权码说明](https://consumer.huawei.com/cn/support/content/zh-cn16108643/)；[SMTP 服务器设置参考](https://developer.cloud.tencent.com/article/2177098)。

## 当前原型的范围

验证状态仅保存在 Streamlit 当前会话中；应用重启或会话丢失后不会保留，也没有关联数据库用户账户。验证码有效期 10 分钟，60 秒后可重发，最多尝试 5 次。

商品现在保存在项目目录中的 `campus_market.db` SQLite 数据库里，首次启动时会添加原有的示例商品。完成邮箱验证后，可以填写名称、分类、价格、昵称和描述发布商品。开发演示模式可以通过页面显示的验证码进入发布流程，不代表真实学生身份验证。

## 发布给同学访问

Streamlit Community Cloud 可从 GitHub 仓库部署。可使用私有 GitHub 仓库，并将应用设为仅指定邮箱可查看；受邀者登录后才能打开网址。部署时在应用的 Secrets 设置里填写上述 SMTP 配置，并设 `EMAIL_VERIFY_MODE="smtp"`；不要把 `.env` 或授权码上传到 GitHub。[Streamlit 官方部署说明](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)；[私有应用分享说明](https://docs.streamlit.io/deploy/streamlit-community-cloud/share-your-app)；[官方密钥管理说明](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management)。

注意：目前商品数据库是本地 SQLite 文件。Community Cloud 不保证本地文件持久保存，所以适合先公开演示；正式让同学长期发布商品前，需要换成云端数据库。[Streamlit 关于数据连接与 SQLite 的说明](https://docs.streamlit.io/develop/concepts/connections/connecting-to-data)。

## 配置云端 PostgreSQL

应用支持通过 `DATABASE_URL` 使用托管 PostgreSQL；没有设置时，本机仍用 `campus_market.db`。以 Supabase 为例：创建项目后，在项目的 **Connect** 面板复制连接 URI（建议使用 Session pooler），把 URI 中的密码在本机替换好，再添加到 Streamlit 的 Secrets 中，键名为 `DATABASE_URL`。不要把 URI 或数据库密码提交到 GitHub 或发到聊天里。

首次连接时应用会创建 `products` 表，并在表为空时加入示例商品。切换云数据库后，本机 SQLite 中的商品不会自动迁移。Supabase 文档建议从 **Connect** 面板复制实际连接字符串，不要自行拼接主机名或用户名。[Supabase 连接说明](https://supabase.com/docs/guides/database/connecting-to-postgres)。

正式上线前应建立真正的用户账户系统，在服务端加入跨会话频率限制、持久化邮箱验证状态、站点级密钥管理和商品管理权限。
