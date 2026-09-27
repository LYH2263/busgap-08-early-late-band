# BusGap 公交串车检测

对比计划发车间隔与实际到站间隔，识别串车与大间隔，并给出调班建议。

技术栈：Python 3.12 / FastAPI / SQLAlchemy / PostgreSQL / Vue 3 / TypeScript / Vite

## 启动

```bash
docker compose up --build
```

| 服务 | 地址 |
| --- | --- |
| 前端 | http://localhost:4600 |
| API | http://localhost:9600 |
| API 文档 | http://localhost:9600/docs |
| Postgres | localhost:5447 |

健康检查：`GET http://localhost:9600/api/health`

## 使用说明

1. 在「线路」查看运营线路与阈值，并可编辑每线的允许早到 / 允许晚到带宽（分钟，持久化保存）。
2. 在「班次」「到站」核对计划与实际到站时间。
3. 打开「串车报告」：班次相对「计划发车 + 沿途计划走行」超出带宽先标偏离且不参与配对，带宽内班次再按串车 / 大间隔阈值两两判定；两带宽都为 0 时只判间隔。
4. 在「时间轴」观察到站分布，在「建议」查看偏离 / 串车 / 大间隔调班提示。

## 开发与测试

```bash
docker compose exec api pytest -q
```
