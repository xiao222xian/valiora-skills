# 分析目录与 NetworkX 示例覆盖

参照 NetworkX 示例库（networkx.org/documentation/stable/auto_examples）。

## 三张图

- **B**：好友—群二部图，用于连通性、介数、接近度、α/β 核、关节点。
- **P**：好友投影，Newman 合作网络加权，同在 n 位好友的群记 1/(n−1)；大群几乎不增加关系强度。
- **P50**：只用好友数 ≤ `--cap` 的群投影，用于聚集系数、k 核、结构洞、富人俱乐部、谱分析。

## 已覆盖

| 示例 | 做法 | results 键 |
| --- | --- | --- |
| Properties / Degree Analysis / Degree Sequence | 规模、度分布、集中度与基尼 | `properties` |
| Giant Component / Decomposition | 连通块、关节点、唯一纽带群 | `properties` `fragility` |
| Erdos Renyi / Expected Degree Sequence | 二部配置模型随机基线 | `smallworld` |
| Find Shortest Path | 抽样 BFS 的好友间距离分布 | `smallworld` |
| Betweenness / Parallel Betweenness | 抽样介数 | `centrality` |
| Krackhardt Centrality | 多种中心性 Spearman 对比、低调的桥 | `centrality` |
| Davis Club | 加权投影、Latapy 聚集、冗余度、群重叠 | `projection` `bipartite` |
| Bipartite Motifs: α/β-core | α×β 网格与深核（剪枝实现） | `abcore` |
| Community Detection (Girvan–Newman) | 核心圈子图上的 GN | `communities.girvanNewman` |
| Blockmodel | 结构社区间连边密度 | `communities.block` |
| Karate Club（同类社区检测） | Louvain / CNM / 标签传播对比 | `communities.compare` |
| Minimum Spanning Tree | 群重叠（1−Jaccard）最小生成树 | `bipartite.mst` |
| TrustRank | 以核心圈为种子的个性化 PageRank | `trustrank` |
| Subgraphs / Ego Graph | 核心圈、深核子图；二跳可达 | 多处 |
| Dedensification | 枢纽压缩率 | `dedensify` |
| SNAP Graph Summary | 按属性分组计数；完整 SNAP 需 `--snap-timeout` | `snap` |
| Eigenvalues / Spectral Embedding | 归一化拉普拉斯谱、代数连通度 | `spectral` |
| 示例外补充 | Burt 结构洞、k 核、洋葱分解、富人俱乐部、同配性 | 对应键 |

## 不运行的示例

| 示例 | 原因 |
| --- | --- |
| Triads、Circuits、Cycle Detection、DAG、LCA | 面向有向图或树 |
| Beam Search、TSP、Maximum Independent Set、Greedy Coloring、Metric Closure | 组合优化，对社交关系无解释力 |
| Reverse Cuthill–McKee、Iterated Dynamical Systems、Image Segmentation | 矩阵排序、动力系统、图像问题 |
| Geospatial 全部 | 没有地理坐标 |
| Drawing / 3D / Graphviz | 绘图示范 |

## 已知问题与性能

- `networkx.constraint` 为纯 Python，稠密投影上每个高连接节点需数秒；脚本以稀疏矩阵实现同一公式，
  与 networkx 逐节点结果误差 < 1e-15。
- networkx 3.7 的 `effective_size` 在加权且不指定 nodes 时走稀疏快速路径，结果与其逐节点公式不一致；
  本 Skill 采用逐节点公式的定义。
- `snap_aggregation` 在上千节点的好友—群子图上可能数分钟不结束，默认跳过。
- 约 1 万好友规模的总耗时：导出 2–3 分钟，分析 3–5 分钟。
