import requests
import time
import random
import hmac
import hashlib
import base64
import urllib.parse
import os
import json
from datetime import datetime, timedelta

# ==================== 配置区域 ====================
API_URL = "https://app.lkdyw.cn/Beta_v2/sign.php"

# 完整的30个用户名列表
USERNAMES = [
    "lekansp", "momuser", "abcd123", "我不想上班22222222", "yujingchao",
    "fgo666", "fanqie66", "todoto11", "qazwsx123", "huwei123",
    "godlike0", "liubei540", "luf21111", "liangj90", "lujy9324",
    "guq91463", "meiq8135", "jiangaj5", "gann9127", "pande193",
    "xiaor307", "feib8129", "hul77020", "tiancs29", "zhanzh25",
    "wudg1330", "diaosg37", "changs19", "leibc509", "wane7840"
]

# 请求头
HEADERS = {
    "Host": "app.lkdyw.cn",
    "Origin": "https://app.lkdyw.cn",
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; TAS-AN00 Build/HUAWEITAS-AN00; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/74.0.3729.186 Mobile Safari/537.36 AgentWeb/5.0.8  UCBrowser/11.6.4.950",
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept": "*/*",
    "Referer": "https://app.lkdyw.cn/Beta_v1/",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "X-Requested-With": "com.lookvideo",
    "Connection": "keep-alive"
}

# 请求间隔范围（秒）【已修改为5-10秒】
INTERVAL_MIN = 5
INTERVAL_MAX = 10

# 钉钉配置
DINGTALK_WEBHOOK = os.getenv('DINGTALK_WEBHOOK')
DINGTALK_SECRET = os.getenv('DINGTALK_SECRET')
DINGTALK_KEYWORD = "签到"
# =================================================

# ==================== 钉钉通知函数 ====================
def get_beijing_time():
    """获取北京时间（UTC+8）"""
    return datetime.utcnow() + timedelta(hours=8)

def get_beijing_time_str():
    """获取北京时间字符串"""
    return get_beijing_time().strftime("%Y-%m-%d %H:%M:%S")

def send_dingtalk_notification(summary, details_md="", full_logs=""):
    """发送钉钉Markdown通知"""
    if not DINGTALK_WEBHOOK:
        print("⚠️ 未配置钉钉Webhook，跳过通知")
        return
    
    if DINGTALK_KEYWORD not in summary:
        summary = f"{DINGTALK_KEYWORD}：{summary}"
    
    webhook_url = DINGTALK_WEBHOOK
    if DINGTALK_SECRET and DINGTALK_SECRET.strip():
        timestamp = str(round(time.time() * 1000))
        secret_enc = DINGTALK_SECRET.encode('utf-8')
        string_to_sign = '{}\n{}'.format(timestamp, DINGTALK_SECRET)
        string_to_sign_enc = string_to_sign.encode('utf-8')
        hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        webhook_url = f"{webhook_url}&timestamp={timestamp}&sign={sign}"
    
    message = {
        "msgtype": "markdown",
        "markdown": {
            "title": summary,
            "text": f"### {summary}\n\n{details_md}\n\n---\n**执行时间（北京时间）**：{get_beijing_time_str()}"
        }
    }
    
    if full_logs:
        if len(full_logs.encode('utf-8')) > 15000:
            full_logs = full_logs[:15000] + "\n\n...日志过长，已截断..."
        message["markdown"]["text"] += f"\n\n#### 📄 完整日志\n\n```\n{full_logs}\n```"
    
    try:
        response = requests.post(webhook_url, json=message, timeout=5)
        result = response.json()
        if result.get("errcode") != 0:
            print(f"❌ 钉钉通知发送失败: {result}")
        else:
            print("✅ 钉钉通知发送成功")
    except Exception as e:
        print(f"❌ 钉钉通知异常: {e}")

# ==================== 日志收集器 ====================
class LogCollector:
    """收集所有日志，用于发送给钉钉"""
    def __init__(self):
        self.logs = []
    
    def add(self, level, message):
        """【已修改为北京时间】"""
        beijing_time_str = get_beijing_time().strftime("%H:%M:%S")
        log_entry = f"[{beijing_time_str}] [{level}] {message}"
        self.logs.append(log_entry)
        print(log_entry)
    
    def info(self, message):
        self.add("INFO", message)
    
    def error(self, message):
        self.add("ERROR", message)
    
    def debug(self, message):
        self.add("DEBUG", message)
    
    def get_all_logs(self):
        return "\n".join(self.logs)
    
    def get_filtered_logs(self):
        return "\n".join([log for log in self.logs if "DEBUG" not in log])

# ==================== 主业务逻辑 ====================
def send_sign_request(username, log_collector):
    """发送签到请求"""
    data = f"username={username}"
    
    try:
        response = requests.post(API_URL, headers=HEADERS, data=data, timeout=10)
        status_code = response.status_code
        
        try:
            json_resp = response.json()
            message = json_resp.get('message', json_resp.get('msg', '无message字段'))
        except:
            message = response.text[:200] if response.text else '无法解析响应'
        
        log_collector.info(f"用户 {username}: 状态码 {status_code}, 响应消息 → {message}")
        
        return {
            "username": username,
            "status": "成功",
            "status_code": status_code,
            "message": message
        }
            
    except requests.exceptions.Timeout:
        error_msg = "请求超时"
        log_collector.error(f"用户 {username}: {error_msg}")
        return {"username": username, "status": "失败", "message": error_msg}
    except requests.exceptions.ConnectionError:
        error_msg = "网络连接错误"
        log_collector.error(f"用户 {username}: {error_msg}")
        return {"username": username, "status": "失败", "message": error_msg}
    except Exception as e:
        error_msg = f"发生错误: {str(e)}"
        log_collector.error(f"用户 {username}: {error_msg}")
        return {"username": username, "status": "失败", "message": error_msg}

def main():
    """主函数"""
    log_collector = LogCollector()
    log_collector.info("========== 开始执行定时签到任务 ==========")
    log_collector.info(f"目标API: {API_URL}")
    log_collector.info(f"钉钉Webhook: {'已配置' if DINGTALK_WEBHOOK else '未配置'}")
    
    if not USERNAMES:
        log_collector.error("错误: 用户名列表为空")
        send_dingtalk_notification(
            summary=f"{DINGTALK_KEYWORD}任务失败：配置错误",
            details_md=f"> **错误详情**：用户名列表为空\n\n请检查代码中的 USERNAMES 配置",
            full_logs=log_collector.get_filtered_logs()
        )
        return
    
    log_collector.info(f"成功加载 {len(USERNAMES)} 个用户名")
    
    success_count = 0
    fail_count = 0
    detailed_results = []
    
    for i, username in enumerate(USERNAMES, 1):
        log_collector.info(f"[{i}/{len(USERNAMES)}] 处理用户: {username}")
        
        result = send_sign_request(username, log_collector)
        detailed_results.append(result)
        
        if result['status'] == '成功':
            success_count += 1
        else:
            fail_count += 1
        
        # 随机间隔【已修改为5-10秒】
        if i < len(USERNAMES):
            sleep_time = random.uniform(INTERVAL_MIN, INTERVAL_MAX)
            log_collector.debug(f"等待 {sleep_time:.2f} 秒...")
            time.sleep(sleep_time)
    
    result_summary = f"任务完成：成功 {success_count}，失败 {fail_count}"
    log_collector.info(f"========== {result_summary} ==========")
    
    details_md = f"#### 📊 执行统计\n\n"
    details_md += f"- **总用户数**：{len(USERNAMES)}\n"
    details_md += f"- **成功**：{success_count} 个\n"
    details_md += f"- **失败**：{fail_count} 个\n\n"
    
    details_md += "#### 📋 详细结果\n\n"
    details_md += "| 序号 | 用户名 | 状态码 | 响应消息 |\n"
    details_md += "| :--- | :--- | :--- | :--- |\n"
    
    for idx, detail in enumerate(detailed_results, 1):
        username = detail.get('username', '未知')
        status = detail.get('status', 'N/A')
        status_code = detail.get('status_code', '-')
        message = detail.get('message', '无消息')
        
        message = message.replace('|', '\\|').replace('\n', ' ')
        if len(message) > 100:
            message = message[:97] + "..."
        
        status_emoji = "✅" if status == "成功" else "❌"
        details_md += f"| {idx} | {username} | {status_emoji} {status_code} | {message} |\n"
    
    if fail_count > 0:
        details_md += "\n#### ⚠️ 失败详情\n\n"
        failed_users = [d for d in detailed_results if d['status'] == '失败']
        for fail in failed_users:
            details_md += f"- **{fail['username']}**: {fail['message']}\n"
    
    print("\n正在发送钉钉通知...")
    send_dingtalk_notification(
        summary=f"{DINGTALK_KEYWORD}任务完成：{result_summary}",
        details_md=details_md,
        full_logs=log_collector.get_filtered_logs()
    )

# ==================== 入口函数 ====================
if __name__ == "__main__":
    main()
