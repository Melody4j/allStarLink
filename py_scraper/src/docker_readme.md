# Neo4j拓扑爬虫 - Docker部署指南

## 前置要求

- Docker已安装
- Docker Compose已安装（可选）

## 构建Docker镜像

在src目录下执行：

```bash
docker build -t neo4j-scraper .
```

## 运行容器

### 方式1：直接运行

```bash
docker run -d \
  --name neo4j-scraper \
  -e LOG_LEVEL=INFO \
  neo4j-scraper
```

### 方式2：使用Docker Compose（推荐）

在项目根目录创建`docker-compose.yml`文件：

```yaml
version: '3.8'

services:
  neo4j-scraper:
    build:
      context: ./src
      dockerfile: Dockerfile
    container_name: neo4j-scraper
    restart: unless-stopped
    environment:
      - LOG_LEVEL=INFO
    # 如果需要访问宿主机的服务，可以使用host网络模式
    # network_mode: host
    # 或者使用端口映射
    # ports:
    #   - "8000:8000"
    volumes:
      # 挂载日志目录
      - ./logs:/app/logs
```

然后运行：

```bash
docker-compose up -d
```

## 查看日志

```bash
docker logs -f neo4j-scraper
```

## 停止容器

```bash
docker stop neo4j-scraper
```

或使用Docker Compose：

```bash
docker-compose down
```

## 重启容器

```bash
docker restart neo4j-scraper
```

## 进入容器

```bash
docker exec -it neo4j-scraper /bin/bash
```

## 环境变量

可以通过以下环境变量配置程序：

### 日志配置
- `LOG_LEVEL`: 日志级别（DEBUG, INFO, WARNING, ERROR, CRITICAL），默认为INFO

### 爬取参数
| 参数 | 说明 | 默认值 | 示例 |
|------|------|--------|------|
| `RATE_LIMIT` | 爬取速率（每分钟请求数） | 60 | 60 |
| `DELAY_MAX` | 爬取最大间隔（秒） | 1 | 1.0 |
| `DELAY_MIN` | 爬取最小间隔（秒） | 0.8 | 0.8 |
| `COOLDOWN` | 限速时冷却时间（秒） | 30 | 30 |

### 使用示例

#### 方式1：docker run 命令
```bash
docker run -d \
  --name neo4j-scraper \
  -e RATE_LIMIT=60 \
  -e DELAY_MAX=1 \
  -e DELAY_MIN=0.8 \
  -e COOLDOWN=30 \
  -e LOG_LEVEL=INFO \
  neo4j-scraper
```

#### 方式2：docker-compose.yml
```yaml
services:
  neo4j-scraper:
    build:
      context: ./src
      dockerfile: Dockerfile
    container_name: neo4j-scraper
    restart: unless-stopped
    environment:
      - LOG_LEVEL=INFO
      - RATE_LIMIT=60
      - DELAY_MAX=1
      - DELAY_MIN=0.8
      - COOLDOWN=30
    volumes:
      - ./logs:/app/logs
```

#### 方式3：使用.env文件
创建`.env`文件：
```
LOG_LEVEL=INFO
RATE_LIMIT=60
DELAY_MAX=1
DELAY_MIN=0.8
COOLDOWN=30
```

在`docker-compose.yml`中引用：
```yaml
services:
  neo4j-scraper:
    env_file:
      - .env
```

### 参数调整建议

#### 低速爬取（避免限流）
```yaml
RATE_LIMIT=30
DELAY_MAX=2
DELAY_MIN=1.5
COOLDOWN=60
```

#### 高速爬取（测试环境）
```yaml
RATE_LIMIT=120
DELAY_MAX=0.5
DELAY_MIN=0.3
COOLDOWN=15
```

#### 标准配置（生产环境）
```yaml
RATE_LIMIT=60
DELAY_MAX=1
DELAY_MIN=0.8
COOLDOWN=30
```

## 注意事项

1. 确保Redis、Neo4j和MySQL服务可访问
2. 如果使用Docker网络，确保容器可以访问这些服务
3. 如果服务在宿主机上，使用`network_mode: host`或正确配置端口映射
4. 生产环境建议使用Docker Compose进行管理
5. 定期检查日志文件，确保程序正常运行
