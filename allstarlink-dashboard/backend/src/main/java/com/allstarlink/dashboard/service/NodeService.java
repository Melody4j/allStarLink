package com.allstarlink.dashboard.service;

import com.allstarlink.dashboard.entity.Node;
import com.allstarlink.dashboard.mapper.NodeMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.Caching;
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

    // 获取所有节点 - 缓存2分钟
    @Cacheable(value = "allNodes", key = "'all'")
    public List<Node> getAllNodes() {
        log.info("从数据库获取所有节点数据");
        List<Node> nodes = nodeMapper.selectAll();
        nodes.forEach(this::setActiveStatus);
        log.info("获取到 {} 个节点", nodes.size());
        return nodes;
    }
    
    // 分页获取节点 - 缓存1分钟
    @Cacheable(value = "nodesByPage", key = "#pageNum + '_' + #pageSize")
    public Map<String, Object> getNodesByPage(int pageNum, int pageSize) {
        log.info("从数据库获取分页节点数据: page={}, size={}", pageNum, pageSize);
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

    // 根据节点ID获取节点 - 缓存5分钟
    @Cacheable(value = "nodeById", key = "#nodeId")
    public Optional<Node> getNodeById(Integer nodeId) {
        log.info("从数据库获取节点详情: nodeId={}", nodeId);
        Optional<Node> node = nodeMapper.selectByNodeId(nodeId);
        node.ifPresent(this::setActiveStatus);
        return node;
    }

    // 获取所有活跃节点 - 缓存1分钟
    @Cacheable(value = "activeNodes", key = "'active'")
    public List<Node> getActiveNodes() {
        log.info("从数据库获取活跃节点数据");
        // 使用 is_active 字段判断节点是否活跃，而不是时间阈值
        List<Node> nodes = nodeMapper.selectAll();
        List<Node> activeNodes = nodes.stream()
                .filter(node -> node.getIsActive() != null && node.getIsActive())
                .peek(node -> node.setIsActive(true))
                .collect(Collectors.toList());
        log.info("获取到 {} 个活跃节点", activeNodes.size());
        return activeNodes;
    }

    // 获取限定数量的活跃节点 - 用于地图优化显示
    @Cacheable(value = "limitedActiveNodes", key = "#limit + '_' + #sortBy")
    public List<Node> getLimitedActiveNodes(int limit, String sortBy) {
        log.info("获取限定数量的活跃节点: limit={}, sortBy={}", limit, sortBy);

        List<Node> allActiveNodes = nodeMapper.selectAll()
                .stream()
                .filter(node -> node.getIsActive() != null && node.getIsActive())
                .peek(node -> node.setIsActive(true))
                .collect(Collectors.toList());

        // 根据sortBy参数排序
        switch (sortBy) {
            case "lastSeen":
                // 按最近在线时间排序
                allActiveNodes.sort((a, b) -> {
                    if (a.getLastSeen() == null && b.getLastSeen() == null) return 0;
                    if (a.getLastSeen() == null) return 1;
                    if (b.getLastSeen() == null) return -1;
                    return b.getLastSeen().compareTo(a.getLastSeen());
                });
                break;
            case "nodeId":
            default:
                // 按节点ID排序
                allActiveNodes.sort((a, b) -> b.getNodeId().compareTo(a.getNodeId()));
                break;
        }

        // 限制返回数量
        List<Node> result = allActiveNodes.stream()
                .limit(limit)
                .collect(Collectors.toList());

        log.info("返回 {} 个活跃节点（总共 {} 个活跃节点）", result.size(), allActiveNodes.size());
        return result;
    }

    public List<Map<String, Object>> getNodeStatsByCountry(int timeThresholdHours) {
        return null;
    }

    // 获取全局统计 - 缓存30秒
    @Cacheable(value = "globalStats", key = "#timeThresholdHours")
    public Map<String, Object> getGlobalStats(int timeThresholdHours) {
        log.info("从数据库计算全局统计数据: timeThresholdHours={}", timeThresholdHours);
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
        log.info("全局统计计算完成: 总节点={}, 活跃节点={}, 活跃比例={}%",
                totalNodes, activeNodes, activePercentage);

        return stats;
    }

    /**
     * 清除所有节点相关的缓存
     * 当节点数据发生变化时调用此方法
     */
    @Caching(evict = {
        @CacheEvict(value = "allNodes", allEntries = true),
        @CacheEvict(value = "activeNodes", allEntries = true),
        @CacheEvict(value = "globalStats", allEntries = true),
        @CacheEvict(value = "nodesByPage", allEntries = true),
        @CacheEvict(value = "nodeById", allEntries = true)
    })
    public void clearAllNodeCache() {
        log.info("清除所有节点相关缓存");
    }

    /**
     * 清除指定节点的缓存
     */
    @CacheEvict(value = "nodeById", key = "#nodeId")
    public void clearNodeCache(Integer nodeId) {
        log.info("清除节点缓存: nodeId={}", nodeId);
    }

    // 设置节点活跃状态
    private void setActiveStatus(Node node) {
        // 使用数据库中的 is_active 字段来判断节点在线状态
        node.setIsActive(node.getIsActive() != null && node.getIsActive());
    }
}