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
API_URL = "https://app.lkdyw.cn/Bate_v2/sign.php"

USERNAMES = [
    "lekansp", "momuser", "abcd123", "我不想上班22222222", "yujingchao",
    "fgo666", "fanqie66", "todoto11", "qazwsx123", "huwei123",
    "godlike0", "liubei540", "luf21111", "liangj90", "lujy9324",
    "guq91463", "meiq8135", "jiangaj5", "gann9127", "pande193",
    "xiaor307", "feib8129", "hul77020", "tiancs29", "zhanzh25",
    "wudg1330", "diaosg37", "changs19", "leibc509", "wane7840",
    "147258369888", "shaoq372", "mit64225", "gongr924", "gongz268", 
    "changpf5", "meizu620", "cenq2545", "quir0845", "piru2475", 
    "jin00964", "boy90272", "yuip6438", "ceno8448", "mod52173", 
    "qivl9379", "chengqc8", "langm033", "qiangr75", "chengjj0", 
    "zhongn15", "jinkj425", "tangkv85", "kangd234", "longw924", 
    "xiongb88", "langry45", "bol77750", "jiangu25", "penggs94", 
    "kuip9346", "boen9620", "boj03613", "bor45330","qiangsu3",
    "pangul33", "shaon776", "shix4515", "mengw601", "kongwx35", "yanqiao567"
]

HEADERS = {
    "Host": "app.lkdyw.cn",
    "Connection": "keep-alive",
    "User-Agent": "Mozilla/5.0 (Linux; Android 12; TAS-AN00 Build/HUAWEITAS-AN00; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/94.0.4606.85 Mobile Safari/537.36 AgentWeb/5.0.8  UCBrowser/11.6.4.950",
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept": "*/*",
    "Origin": "https://app.lkdyw.cn",
    "X-Requested-With": "com.lookvideo",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Dest": "empty",
    "Referer": "https://app.lkdyw.cn/Bate_v2/",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7"
}

INTERVAL_MIN = 5
INTERVAL_MAX = 12

DINGTALK_WEBHOOK = os.getenv('DINGTALK_WEBHOOK')
DINGTALK_SECRET = os.getenv('DINGTALK_SECRET')
DINGTALK_KEYWORD = "签到"

# ==================== 用户名保护功能（修复脱敏逻辑） ====================
def mask_username(username):
    """
    隐藏用户名中间部分，只显示前后字符（修复：确保所有长度用户名都带*）
    
    规则优化：
    - 用户名长度 1：直接返回 *
    - 用户名长度 2：显示前1后1，中间用*填充（如 ab → a*b）
    - 用户名长度 3-4：显示前1后1，中间用*填充（如 abc → a*c，abcd → a**d）
    - 用户名长度 5-6：显示前2后2，中间用*填充（如 abcde → ab*de，abcdef → ab**ef）
    - 用户名长度 > 6：显示前3后3，中间用*填充（如 abcdefg → abc*efg）
    """
    if not username:
        return "***"
    
    length = len(username)
    
    if length == 1:
        return "*"
    elif length == 2:
        return username[0] + "*" + username[-1]
    elif length <= 4:
        return username[0] + "*" * (length - 2) + username[-1]
    elif length <= 6:
        return username[:2] + "*" * (length - 4) + username[-2:]
    else:
        front = 3
        back = 3
        return username[:front] + "*" * (length - front - back) + username[-back:]
# =================================================

def get_beijing_time():
    return datetime.utcnow() + timedelta(hours=8)

def get_beijing_time_str():
    return get_beijing_time().strftime("%Y-%m-%d %H:%M:%S")

def send_dingtalk_notification(summary, details_md="", full_logs=""):
    """
    发送钉钉Markdown通知（修改：默认不携带完整日志）
    """
    if not DINGTALK_WEBHOOK:
        print("⚠️ 未配置钉钉Webhook，跳过通知")
        return False
    
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
        webhook_url = f"{DINGTALK_WEBHOOK}&timestamp={timestamp}&sign={sign}"
    
    message = {
        "msgtype": "markdown",
        "markdown": {
            "title": summary,
            # 关键修改1：删除 full_logs 拼接，只保留统计和详细结果
            "text": f"### {summary}\n\n{details_md}\n\n---\n**执行时间（北京时间）**：{get_beijing_time_str()}"
        }
    }
    
    try:
        response = requests.post(webhook_url, json=message, timeout=5)
        result = response.json()
        if result.get("errcode") != 0:
            print(f"❌ 钉钉通知发送失败: {result}")
            print(f"响应内容: {response.text}")
            return False
        else:
            print("✅ 钉钉通知发送成功")
            return True
    except Exception as e:
        print(f"❌ 钉钉通知异常: {e}")
        return False

class LogCollector:
    """收集所有日志，用于GitHub运行记录（新增积分信息存储）"""
    def __init__(self):
        self.logs = []
    
    def add(self, level, message):
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

def send_sign_request(username, log_collector):
    """发送签到请求（关键修改2：提取积分信息并写入日志）"""
    data = f"username={username}"
    
    try:
        response = requests.post(API_URL, headers=HEADERS, data=data, timeout=10)
        status_code = response.status_code
        response_text = response.text
        
        try:
            json_resp = response.json()
            message = json_resp.get('message', json_resp.get('msg', '无message字段'))
            # 提取积分信息（从响应消息中解析）
            score_info = ""
            if "随机奖励" in message and "连续" in message:
                # 匹配格式：签到成功！随机奖励x积分 + 连续y天奖励z积分
                import re
                random_score = re.search(r'随机奖励(\d+)积分', message)
                continuous_score = re.search(r'连续.*奖励(\d+)积分', message)
                if random_score and continuous_score:
                    score_info = f"，随机奖励{random_score.group(1)}积分，连续奖励{continuous_score.group(1)}积分，总积分{int(random_score.group(1)) + int(continuous_score.group(1))}分"
        except:
            message = response_text[:200] if response_text else '无法解析响应'
            score_info = ""
        
        success = is_success(status_code, response_text)
        
        if success:
            # 关键修改3：日志中添加积分信息
            log_collector.info(f"用户 {username}: ✅ 成功，状态码 {status_code}{score_info}")
        else:
            short_msg = message[:50] + "..." if len(message) > 50 else message
            log_collector.error(f"用户 {username}: ❌ 失败，状态码 {status_code}, 消息: {short_msg}")
        
        return {
            "username": username,
            "status": "成功" if success else "失败",
            "status_code": status_code,
            "message": message,
            "success": success,
            "score_info": score_info  # 存储积分信息，用于后续日志
        }
            
    except requests.exceptions.Timeout:
        error_msg = "请求超时"
        log_collector.error(f"用户 {username}: ❌ {error_msg}")
        return {"username": username, "status": "失败", "message": error_msg, "success": False, "score_info": ""}
    except requests.exceptions.ConnectionError:
        error_msg = "网络连接错误"
        log_collector.error(f"用户 {username}: ❌ {error_msg}")
        return {"username": username, "status": "失败", "message": error_msg, "success": False, "score_info": ""}
    except Exception as e:
        error_msg = f"发生错误: {str(e)}"
        log_collector.error(f"用户 {username}: ❌ {error_msg}")
        return {"username": username, "status": "失败", "message": error_msg, "success": False, "score_info": ""}

def is_success(status_code, response_text):
    """判定请求是否真正成功"""
    if not status_code or not (200 <= status_code < 300):
        return False
    
    error_indicators = ["404 Not Found", "500 Internal", "错误", "Error", "<html>"]
    if any(indicator in response_text for indicator in error_indicators):
        return False
    
    return True

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
            details_md=f"> **错误详情**：用户名列表为空\n\n请检查代码中的 USERNAMES 配置"
        )
        return
    
    log_collector.info(f"成功加载 {len(USERNAMES)} 个用户名")
    
    success_count = 0
    fail_count = 0
    detailed_results = []
    total_score = 0  # 新增：统计总积分
    
    for i, username in enumerate(USERNAMES, 1):
        log_collector.info(f"[{i}/{len(USERNAMES)}] 处理用户: {username}")
        
        result = send_sign_request(username, log_collector)
        detailed_results.append(result)
        
        if result.get('success', False):
            success_count += 1
            # 累加总积分
            if result.get('score_info'):
                import re
                total = re.search(r'总积分(\d+)分', result['score_info'])
                if total:
                    total_score += int(total.group(1))
        
        else:
            fail_count += 1
        
        if i < len(USERNAMES):
            sleep_time = random.uniform(INTERVAL_MIN, INTERVAL_MAX)
            log_collector.debug(f"等待 {sleep_time:.2f} 秒...")
            time.sleep(sleep_time)
    
    # 关键修改4：任务总结日志添加总积分统计
    result_summary = f"任务完成：成功 {success_count}，失败 {fail_count}，总获得积分 {total_score} 分"
    log_collector.info(f"========== {result_summary} ==========")
    
    details_md = f"#### 📊 执行统计\n\n"
    details_md += f"- **总用户数**：{len(USERNAMES)}\n"
    details_md += f"- **成功**：{success_count} 个\n"
    details_md += f"- **失败**：{fail_count} 个\n"
    details_md += f"- **总获得积分**：{total_score} 分\n\n"  # 钉钉通知添加总积分
    
    details_md += "#### 📋 详细结果\n\n"
    details_md += "| 序号 | 用户名 | 状态码 | 响应消息 |\n"
    details_md += "| :--- | :--- | :--- | :--- |\n"
    
    for idx, detail in enumerate(detailed_results, 1):
        masked_username = mask_username(detail.get('username', 'unknown'))
        status_code = detail.get('status_code', '-')
        message = detail.get('message', '无消息')
        
        message = message.replace('|', '\\|').replace('\n', ' ')
        if len(message) > 100:
            message = message[:97] + "..."
        
        is_user_success = detail.get('success', False)
        status_emoji = "✅" if is_user_success else "❌"
        details_md += f"| {idx} | {masked_username} | {status_emoji} {status_code} | {message} |\n"
    
    if fail_count > 0:
        details_md += "\n#### ⚠️ 失败详情\n\n"
        failed_users = [d for d in detailed_results if not d.get('success', False)]
        for fail in failed_users:
            masked_username = mask_username(fail.get('username', 'unknown'))
            details_md += f"- **{masked_username}**: {fail['message']}\n"
    
    print("\n正在发送钉钉通知...")
    # 关键修改5：调用时不传递 full_logs 参数，隐藏完整日志
    dingtalk_success = send_dingtalk_notification(
        summary=f"{DINGTALK_KEYWORD}任务完成：{result_summary}",
        details_md=details_md
    )
    
    if not dingtalk_success:
        log_collector.error("=" * 50)
        log_collector.error("⚠️ 钉钉通知发送失败！请检查日志！")
        log_collector.error(f"任务结果: {result_summary}")
        log_collector.error("=" * 50)

# ==================== 入口函数 ====================
if __name__ == "__main__":
    main()

