package com.allstarlink.dashboard.service;

import com.allstarlink.dashboard.entity.Node;
import com.allstarlink.dashboard.mapper.NodeMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.*;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Slf4j
public class NodeService {

    private final NodeMapper nodeMapper;
    private final GeocodingService geocodingService;

    // 默认活跃时间阈值：24小时
    private static final int ACTIVE_TIME_THRESHOLD = 24;

    // 获取所有节点
    public List<Node> getAllNodes() {
        List<Node> nodes = nodeMapper.selectAll();
        nodes.forEach(this::setActiveStatus);
        return nodes;
    }
    
    // 分页获取节点
    public Map<String, Object> getNodesByPage(int pageNum, int pageSize) {
        // 使用 PageHelper 实现分页
        com.github.pagehelper.PageHelper.startPage(pageNum, pageSize);
        List<Node> nodes = nodeMapper.selectAll();
        nodes.forEach(this::setActiveStatus);
        
        // 获取分页信息
        com.github.pagehelper.PageInfo<Node> pageInfo = new com.github.pagehelper.PageInfo<>(nodes);
        
        // 构建返回结果
        Map<String, Object> result = new HashMap<>();
        result.put("total", pageInfo.getTotal());
        result.put("list", pageInfo.getList());
        result.put("pageNum", pageInfo.getPageNum());
        result.put("pageSize", pageInfo.getPageSize());
        result.put("pages", pageInfo.getPages());
        
        return result;
    }

    // 根据节点ID获取节点
    public Optional<Node> getNodeById(Integer nodeId) {
        Optional<Node> node = nodeMapper.selectByNodeId(nodeId);
        node.ifPresent(this::setActiveStatus);
        return node;
    }

    // 获取所有活跃节点
    public List<Node> getActiveNodes() {
        // 使用 is_active 字段判断节点是否活跃，而不是时间阈值
        List<Node> nodes = nodeMapper.selectAll();
        return nodes.stream()
                .filter(node -> node.getIsActive() != null && node.getIsActive())
                .peek(node -> node.setIsActive(true))
                .collect(Collectors.toList());
    }

    // 根据位置查询节点
    public List<Node> getNodesByLocation(String location) {
        List<Node> nodes = nodeMapper.selectByLocationContaining(location);
        nodes.forEach(this::setActiveStatus);
        return nodes;
    }

    // 获取按位置分组的节点统计（带缓存）
    @Cacheable(value = "nodeStatsByLocation", key = "#timeThresholdHours")
    public List<Map<String, Object>> getNodeStatsByLocation(int timeThresholdHours) {
        LocalDateTime timeThreshold = LocalDateTime.now().minusMinutes(10);
        return nodeMapper.selectNodeStatsByLocation(timeThreshold);
    }

    // 获取按国家分组的节点统计（带缓存）
    @Cacheable(value = "nodeStatsByCountry", key = "#timeThresholdHours")
    public List<Map<String, Object>> getNodeStatsByCountry(int timeThresholdHours) {
        log.info("开始获取国家统计数据...");
        
        // 获取所有节点，而不是只获取活跃节点，因为我们需要计算总节点数和活跃节点数
        List<Node> allNodes = getAllNodes();
        
        log.info("获取到 {} 个节点", allNodes.size());
        
        // 创建国家统计映射，key为国家名称，value为统计信息
        Map<String, Map<String, Object>> countryStatsMap = new HashMap<>();
        
        // 用于记录已经处理过的经纬度，避免重复调用地理编码API
        Map<String, String> latLngCountryCache = new HashMap<>();
        
        // 遍历所有节点
        for (Node node : allNodes) {
            try {
                // 获取节点的经纬度
                Double latitude = node.getLatitude();
                Double longitude = node.getLongitude();
                
                String country = "other"; // 默认国家为other
                
                // 如果节点有经纬度，使用高德地图API获取国家信息
                if (latitude != null && longitude != null && latitude != 0 && longitude != 0) {
                    // 生成经纬度字符串作为缓存key，保留4位小数
                    String latLngKey = String.format("%.4f,%.4f", latitude, longitude);
                    
                    // 检查缓存中是否已经有该经纬度的国家信息
                    if (latLngCountryCache.containsKey(latLngKey)) {
                        country = latLngCountryCache.get(latLngKey);
                        log.debug("使用缓存的国家信息: 经纬度 {} 对应的国家: {}", latLngKey, country);
                    } else {
                        // 调用地理编码服务获取国家信息
                        country = geocodingService.getCountryFromCoordinates(latitude, longitude);
                        log.debug("经纬度 {} 对应的国家: {}", latLngKey, country);
                        
                        // 将结果存入缓存
                        latLngCountryCache.put(latLngKey, country);
                    }
                }
                
                // 获取该国家的统计信息，如果不存在则创建
                Map<String, Object> countryStat = countryStatsMap.computeIfAbsent(country, k -> {
                    Map<String, Object> stat = new HashMap<>();
                    stat.put("country", k);
                    stat.put("totalNodes", 0L);
                    stat.put("activeNodes", 0L);
                    return stat;
                });
                
                // 更新统计信息
                countryStat.put("totalNodes", (Long) countryStat.get("totalNodes") + 1);
                if (node.getIsActive() != null && node.getIsActive()) {
                    countryStat.put("activeNodes", (Long) countryStat.get("activeNodes") + 1);
                }
                
            } catch (Exception e) {
                log.error("处理节点 {} 时出错: {}", node.getNodeId(), e.getMessage());
                log.error("节点数据: {}", node);
            }
        }
        
        // 将映射转换为列表并按总节点数排序
        List<Map<String, Object>> result = new ArrayList<>(countryStatsMap.values());
        result.sort((a, b) -> Long.compare((Long) b.get("totalNodes"), (Long) a.get("totalNodes")));
        
        log.info("国家统计数据生成完成，共 {} 个国家", result.size());
        log.debug("国家统计数据: {}", result);
        
        return result;
    }

    // 获取全局统计信息（带缓存）
    @Cacheable(value = "globalStats", key = "#timeThresholdHours")
    public Map<String, Object> getGlobalStats(int timeThresholdHours) {
        // 从数据库获取统计数据
        List<Node> nodes = nodeMapper.selectAll();
        
        // 计算总节点数
        long totalNodes = nodes.size();
        
        // 计算活跃节点数
        long activeNodes = nodes.stream()
                .filter(node -> node.getIsActive() != null && node.getIsActive())
                .count();
        
        // 计算活跃比例
        double activePercentage = totalNodes > 0 ? (activeNodes * 100.0 / totalNodes) : 0.0;
        
        // 构建返回结果
        Map<String, Object> stats = new HashMap<>();
        stats.put("totalNodes", totalNodes);
        stats.put("activeNodes", activeNodes);
        stats.put("activePercentage", Math.round(activePercentage * 10) / 10.0); // 保留一位小数
        stats.put("timeThreshold", timeThresholdHours);
        stats.put("timestamp", LocalDateTime.now());
        
        return stats;
    }

    // 根据地理范围获取节点
    public List<Node> getNodesByGeoBounds(double minLat, double maxLat, double minLon, double maxLon) {
        List<Node> nodes = nodeMapper.selectNodesByGeoBounds(minLat, maxLat, minLon, maxLon);
        nodes.forEach(this::setActiveStatus);
        return nodes;
    }

    // 设置节点活跃状态
    private void setActiveStatus(Node node) {
        // 使用数据库中的 is_active 字段来判断节点在线状态
        node.setIsActive(node.getIsActive() != null && node.getIsActive());
    }
}