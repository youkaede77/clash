# 完整分流的紧凑规则数据

本目录由同一个每日更新工作流生成，只包含公开规则，不包含客户端配置、订阅密钥或代理凭据。

`compact-sources.json` 明确列出全部来源：

- 将原 16 个地区 IP 集按原配置中相邻且目标相同的规则合并为 7 组。IPv4、IPv6 和地区覆盖均保留；组间仍按北美、南美、欧洲、大洋洲、东亚、西亚、非洲的顺序匹配。
- 将 45 份 [Accademia 的公开域名/IP 规则](https://github.com/Accademia/Additional_Rule_For_Clash) 及 [Cloudflare IPv4](https://www.cloudflare.com/ips-v4)、[IPv6](https://www.cloudflare.com/ips-v6) 地址列表转换为原生 MRS。
- 所有 MRS 使用 64 KiB Zstandard 解压窗口。转换使用 Mihomo 自身的规则解析器，并验证文本往返；地区合并另做精确 IP 区间并集比较。未改变规则数据的归属判断，不扩大网段，不删除 IPv6。

为兼容旧配置，原 `rules/regions` 下 16 份独立规则仍会更新。本目录中的地区文件沿用各组第一份规则的名称，但含该组全部地区，具体组成见 `manifest.json` 的 `source_regions`。例如这里的 `GeoRouting_Europe_West_GeoIP.mrs` 包含原东欧和西欧。**只有相邻规则使用同一个目标策略时才能这样合并**，不能直接替换任意配置中目标不同的地区规则。

工作流每日 UTC 03:17 尝试更新；所有数据构建和校验成功后才一并提交。失败保留此前已发布内容。手机配置应设置 `type: http`、`format: mrs`、正确的 `behavior` 和 `interval: 86400`，客户端在运行期间自动更新。GitHub 的调度时间可能延迟。此目录不代表 iPhone 稳定性已经验证。

地区数据来源与 CC BY-SA 4.0 / MaxMind GeoLite2 声明沿用 [原地区规则说明](../regions/README.md#来源与许可)。Accademia 数据的 MIT 许可原文保留在 [licenses/Accademia-MIT.txt](../regions/licenses/Accademia-MIT.txt)。所作修改为合并同去向地区、转换规则格式及重新压缩；其他来源的权利与声明仍归相应提供者。
