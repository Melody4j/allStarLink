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

    public List<Map<String, Object>> getNodeStatsByCountry(int timeThresholdHours) {
        return null;
    }

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

    // 设置节点活跃状态
    private void setActiveStatus(Node node) {
        // 使用数据库中的 is_active 字段来判断节点在线状态
        node.setIsActive(node.getIsActive() != null && node.getIsActive());
    }
}