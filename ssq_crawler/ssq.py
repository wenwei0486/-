import requests
import pandas as pd
import os

# 设置桌面路径（C盘用户桌面）
desktop_path = r"C:\Users\wen\Desktop"
csv_file = os.path.join(desktop_path, "shuangseqiu_data.csv")

# 确保保存目录存在
def ensure_directory_exists(path):
    if not os.path.exists(path):
        os.makedirs(path)
        print(f"创建目录: {path}")

# 爬取双色球数据
def fetch_shuangseqiu_data():
    url = "https://www.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Content-Type": "application/json;charset=UTF-8",
        "Origin": "https://www.cwl.gov.cn",
        "Referer": "https://www.cwl.gov.cn/ygkj/wqkjgg/ssq/"
    }

    # 初始化数据列表
    data_list = []
    page_size = 300  # 每页300期
    target_count = 3000  # 目标获取3000期
    page_no = 1

    while len(data_list) < target_count:
        params = {
            "name": "ssq",
            "issueCount": "",
            "issueStart": "",
            "issueEnd": "",
            "pageNo": str(page_no),
            "pageSize": str(page_size),
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            if response.status_code != 200:
                print(f"请求失败，状态码: {response.status_code}")
                break

            print(f"请求第 {page_no} 页成功，开始解析数据...")
            json_data = response.json()
            if 'result' not in json_data:
                print("API返回数据格式错误")
                break

            for item in json_data['result']:
                # 解析期号和日期
                period = str(item.get('code', ''))  # 期号
                date = item.get('date', '')  # 日期
                # 解析红球和蓝球
                red_balls_str = item.get('red', '')
                blue_ball = item.get('blue', 0)
                # 确保红球和蓝球格式正确
                try:
                    red_balls = [int(num) for num in red_balls_str.split(',')]
                    blue_ball = int(blue_ball)
                except (ValueError, AttributeError) as e:
                    print(f"解析红球或蓝球出错，期号 {period}：{e}")
                    continue
                # 确保红球有 6 个号码
                if len(red_balls) != 6:
                    print(f"红球数量不正确，期号 {period}：{red_balls}")
                    continue
                # 提取销售额和奖池金额
                sales = item.get('sales', 0)  # 销售额
                # 尝试从不同字段获取奖池金额
                pool = item.get('pool', None)
                if pool is None or pool == '0' or pool == '':
                    pool = item.get('prizePool', None) or item.get('poolMoney', None) or item.get('rollover', 0)
                # 提取中奖金额（一等奖和二等奖）
                prizegrades = item.get('prizegrades', [])
                first_prize_num = 0  # 一等奖注数
                first_prize_money = 0  # 一等奖金额
                second_prize_num = 0  # 二等奖注数
                second_prize_money = 0  # 二等奖金额
                for grade in prizegrades:
                    prize_type = grade.get('type', 0)
                    if prize_type == 1:  # 一等奖
                        first_prize_num = int(grade.get('typenum', 0))
                        first_prize_money = int(grade.get('typemoney', 0))
                    elif prize_type == 2:  # 二等奖
                        second_prize_num = int(grade.get('typenum', 0))
                        second_prize_money = int(grade.get('typemoney', 0))
                # 调试：打印完整数据
                print(f"期号: {period}, 完整数据: {item}")
                print(f"期号: {period}, 日期: {date}, 红球: {red_balls}, 蓝球: {blue_ball}, 销售额: {sales}, 奖池金额: {pool}, 一等奖: {first_prize_num}注/{first_prize_money}元, 二等奖: {second_prize_num}注/{second_prize_money}元")
                # 合并数据
                data_list.append([period, date] + red_balls + [blue_ball, first_prize_num, first_prize_money, second_prize_num, second_prize_money, sales, pool])

                # 如果已经达到目标数量，停止
                if len(data_list) >= target_count:
                    break

            # 如果当前页数据少于 page_size，说明已到最后一页
            if len(json_data['result']) < page_size:
                break

            page_no += 1

        except Exception as e:
            print(f"爬取第 {page_no} 页时出错：{e}")
            break

    print(f"成功获取 {len(data_list)} 期数据")
    return data_list[:target_count]  # 确保不超过3000期

# 保存数据到CSV
def save_to_csv(data, update=False):
    # 定义列名（调整顺序，新增中奖金额列）
    columns = ["期号", "日期", "红球1", "红球2", "红球3", "红球4", "红球5", "红球6", "蓝球", "一等奖注数", "一等奖金额", "二等奖注数", "二等奖金额", "销售额", "奖池金额"]
    df_new = pd.DataFrame(data, columns=columns)

    # 确保“期号”列为字符串类型
    df_new["期号"] = df_new["期号"].astype(str)

    # 格式化红球和蓝球（确保两位数字）
    for i in range(1, 7):
        df_new[f"红球{i}"] = df_new[f"红球{i}"].apply(lambda x: f"{int(x):02d}" if isinstance(x, (int, float)) else "00")
    df_new["蓝球"] = df_new["蓝球"].apply(lambda x: f"{int(x):02d}" if isinstance(x, (int, float)) else "00")

    # 格式化金额（去掉“元”单位，保留千位分隔符）
    df_new["一等奖金额"] = df_new["一等奖金额"].apply(lambda x: f"{int(x):,}" if x else "0")
    df_new["二等奖金额"] = df_new["二等奖金额"].apply(lambda x: f"{int(x):,}" if x else "0")
    df_new["销售额"] = df_new["销售额"].apply(lambda x: f"{int(x):,}" if x else "0")
    df_new["奖池金额"] = df_new["奖池金额"].apply(lambda x: f"{int(x):,}" if x else "未知")

    # 确保保存目录存在
    ensure_directory_exists(desktop_path)

    if update and os.path.exists(csv_file):
        # 读取现有数据，并指定“期号”列为字符串类型
        df_old = pd.read_csv(csv_file, dtype={"期号": str})
        # 确保旧数据的“期号”列为字符串类型
        df_old["期号"] = df_old["期号"].astype(str)
        # 合并新旧数据，并以“期号”为准去重（保留最新的）
        df_combined = pd.concat([df_old, df_new]).drop_duplicates(subset=["期号"], keep="last")
        # 按期号降序排序（最新的在前面）
        df_combined = df_combined.sort_values(by="期号", ascending=False)
        # 只保留最新的 3000 期
        df_combined = df_combined.head(3000)
        # 保存合并后的数据
        df_combined.to_csv(csv_file, index=False, encoding="utf-8-sig")
        print(f"数据已更新，保存到 {csv_file}，总共 {len(df_combined)} 期")
    else:
        # 如果没有现有文件，直接保存
        df_new = df_new.sort_values(by="期号", ascending=False)  # 按期号降序排序
        df_new = df_new.head(3000)  # 确保只保存 3000 期
        df_new.to_csv(csv_file, index=False, encoding="utf-8-sig")
        print(f"数据已保存到 {csv_file}，总共 {len(df_new)} 期")

# 主函数
def main():
    print("开始抓取双色球数据...")
    data = fetch_shuangseqiu_data()

    if not data:
        print("未获取到数据，请检查URL或网络连接！")
        return

    # 每次运行都以更新模式保存
    save_to_csv(data, update=True)

if __name__ == "__main__":
    main()