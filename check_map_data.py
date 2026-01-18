import requests

# 地图数据API URL
MAP_DATA_URL = "https://stats.allstarlink.org/api/stats/mapData"

# 发送请求获取地图数据
response = requests.get(MAP_DATA_URL, timeout=30)
response.raise_for_status()

# 解析文本响应
map_data = response.text
lines = map_data.strip().split('\n')

print(f"总数据行数：{len(lines)}")
print(f"节点数量（减去表头）：{len(lines) - 1}")

# 检查前5行数据
print("\n前5行数据：")
for i, line in enumerate(lines[:5]):
    print(f"第{i+1}行: {repr(line)}")

# 统计有效的节点数据
valid_nodes = 0
invalid_nodes = 0

# 跳过表头行，从第二行开始处理
for line in lines[1:]:
    if not line.strip():
        continue
    
    # 分割每行数据，使用制表符作为分隔符
    parts = line.split('\t')
    if len(parts) < 4:
        invalid_nodes += 1
        continue
    
    try:
        node_id = parts[0].strip()
        # 确保node_id是数字
        if not node_id.isdigit():
            invalid_nodes += 1
            continue
        
        # 第三列是纬度，第四列是经度
        latitude = float(parts[2].strip())
        longitude = float(parts[3].strip())
        
        # 验证经纬度是否在有效范围内
        if -90 <= latitude <= 90 and -180 <= longitude <= 180:
            valid_nodes += 1
        else:
            invalid_nodes += 1
    except (ValueError, IndexError):
        invalid_nodes += 1
        continue

print(f"\n有效节点数量：{valid_nodes}")
print(f"无效节点数量：{invalid_nodes}")
print(f"总节点数量：{valid_nodes + invalid_nodes}")
