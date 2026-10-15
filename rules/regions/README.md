# 自动更新的地区 IP 规则集

这 16 份 `ipcidr` / `mrs` 规则将原地区列表引用的国家 IP 网段预先合并，供 Clash Mi / Mihomo 加载。地区列表来自 [Accademia/Additional_Rule_For_Clash](https://github.com/Accademia/Additional_Rule_For_Clash/tree/main/GeoRouting_For_IP)，国家 IP 数据来自 [Loyalsoldier/geoip](https://github.com/Loyalsoldier/geoip)。不包含订阅链接、代理节点、账号密码或 WireGuard 私钥。

## 自动更新

GitHub Actions 每天 UTC 03:17（UTC+8 11:17）检查上游数据，也支持手动运行。只有全部地区成功生成并通过精确 IP 覆盖校验后才提交更新。任何下载、解析、缺失国家、转换或校验错误都会使任务失败，已发布文件继续保留。GitHub 调度可能延迟；客户端 `interval: 86400` 表示核心运行期间按 24 小时更新，并不保证手机系统每天准点唤醒。上游数据未变化时不会创建无意义提交。

工作流需要仓库允许 GitHub Actions，以及该工作流对仓库内容的写权限。生成器固定使用 Mihomo v1.19.32，并校验 Linux 转换器压缩包 SHA-256。`manifest.json` 记录实际输入数据、地区映射和输出 MRS 的校验和，便于审计。

## 客户端引用

```yaml
rule-providers:
  GeoRouting_America_North_GeoIP:
    type: http
    behavior: ipcidr
    format: mrs
    interval: 86400
    url: https://raw.githubusercontent.com/youkaede77/clash/main/rules/regions/GeoRouting_America_North_GeoIP.mrs
    path: ./regions/GeoRouting_America_North_GeoIP.mrs
```

原配置中的 `RULE-SET` 顺序和目标策略组保持不变。原配置的下载代理设置也应保留。首次加载需要下载规则文件；已有缓存时继续使用缓存。客户端需要支持 MRS，不应将这些文件声明成 `classical` 或 `yaml`。

## 校验与本地重建

使用 Python 3.14 标准库（含 compression.zstd）、curl 和 Mihomo：

```sh
python3 -m unittest discover -s scripts -p 'test_*.py' -v
curl --fail --location https://raw.githubusercontent.com/Loyalsoldier/geoip/release/geoip.dat -o /tmp/geoip.dat
python3 scripts/build_regions.py --geoip /tmp/geoip.dat --mihomo /path/to/mihomo --source-url https://raw.githubusercontent.com/Loyalsoldier/geoip/release/geoip.dat --output rules/regions
```

MRS 的 Zstandard 解压窗口限制为 64 KiB，并保留内容校验和。重新压缩前后逐字节验证解码内容相同，以降低并发初始化时的解压缓冲开销；不改变 IP 网段或自动更新方式。

构建先按 IPv4 / IPv6 分别合并网段，再用独立的整数区间并集校验覆盖范围，最后将 MRS 解码回 CIDR 再次校验。不会为了缩小文件而扩大、缩减 IP 覆盖或忽略 IPv6。上游重复的国家规则会去重；其他未知语义会报错。

地区国家归属表会跟随原始地区列表更新。检查 `manifest.json` 中的 `countries` 可以了解每个版本的实际组成。该包只提供规则数据，不保证任一代理节点连通，也不代表已经完成 iPhone 稳定性验证。

## 来源与许可

地区 IP 数据及本目录中合并后的 MRS 数据采用 [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)，保留 [Loyalsoldier/geoip 的许可](https://github.com/Loyalsoldier/geoip/blob/master/LICENSE)。本数据包含由 [MaxMind](https://www.maxmind.com/) 创建的 GeoLite2 数据；Loyalsoldier 的中国大陆地址另采用 [gaoyifan/china-operator-ip](https://github.com/gaoyifan/china-operator-ip)。上游既有修改见其 README。

本项目所作修改：按 Accademia 的地区列表合并多个国家的 IPv4 / IPv6 网段，并转换为 MRS；不声称上游认可或背书。本数据按来源许可中的现状条款提供。

地区列表来源 Accademia/Additional_Rule_For_Clash，MIT 许可原文见 [licenses/Accademia-MIT.txt](licenses/Accademia-MIT.txt)。Mihomo 转换器来自 [MetaCubeX/mihomo](https://github.com/MetaCubeX/mihomo)，只在构建环境下载使用，不包含在此规则包内。
