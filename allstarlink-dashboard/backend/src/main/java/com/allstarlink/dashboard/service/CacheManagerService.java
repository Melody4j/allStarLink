package com.allstarlink.dashboard.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.util.Set;

/**
 * 缓存管理服务
 * 负责监控和管理Redis缓存的状态
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class CacheManagerService {

    private final RedisTemplate<String, Object> redisTemplate;
    private final NodeService nodeService;

    /**
     * 定时清理节点缓存
     * 每2分钟执行一次，与节点数据更新周期同步
     */
    @Scheduled(fixedRate = 120000) // 2分钟 = 120000毫秒
    public void clearNodeCacheScheduled() {
        log.info("定时清理节点缓存开始");
        try {
            // 清除所有节点相关的缓存
            nodeService.clearAllNodeCache();

            // 统计当前缓存数量
            logCacheStats();

            log.info("定时清理节点缓存完成");
        } catch (Exception e) {
            log.error("定时清理节点缓存失败", e);
        }
    }

    /**
     * 手动清理所有缓存
     */
    public void clearAllCache() {
        log.info("手动清理所有缓存开始");
        try {
            Set<String> keys = redisTemplate.keys("*");
            if (keys != null && !keys.isEmpty()) {
                redisTemplate.delete(keys);
                log.info("清理了 {} 个缓存键", keys.size());
            }
            log.info("手动清理所有缓存完成");
        } catch (Exception e) {
            log.error("手动清理缓存失败", e);
        }
    }

    /**
     * 获取缓存统计信息
     */
    public void logCacheStats() {
        try {
            Set<String> allKeys = redisTemplate.keys("*");
            Set<String> nodeKeys = redisTemplate.keys("allNodes*");
            Set<String> activeNodeKeys = redisTemplate.keys("activeNodes*");
            Set<String> statsKeys = redisTemplate.keys("globalStats*");
            Set<String> pageKeys = redisTemplate.keys("nodesByPage*");
            Set<String> byIdKeys = redisTemplate.keys("nodeById*");

            log.info("缓存统计 - 总数: {}, 节点: {}, 活跃节点: {}, 统计: {}, 分页: {}, 详情: {}",
                    allKeys != null ? allKeys.size() : 0,
                    nodeKeys != null ? nodeKeys.size() : 0,
                    activeNodeKeys != null ? activeNodeKeys.size() : 0,
                    statsKeys != null ? statsKeys.size() : 0,
                    pageKeys != null ? pageKeys.size() : 0,
                    byIdKeys != null ? byIdKeys.size() : 0
            );
        } catch (Exception e) {
            log.error("获取缓存统计信息失败", e);
        }
    }

    /**
     * 预热缓存
     * 在应用启动时或缓存清理后预加载常用数据
     */
    public void warmUpCache() {
        log.info("开始预热缓存");
        try {
            // 预加载全局统计数据
            nodeService.getGlobalStats(1);
            nodeService.getGlobalStats(24);

            // 预加载活跃节点（最常访问的数据）
            nodeService.getActiveNodes();

            // 预加载第一页节点数据
            nodeService.getNodesByPage(1, 20);

            log.info("缓存预热完成");
        } catch (Exception e) {
            log.error("缓存预热失败", e);
        }
    }

    /**
     * 检查Redis连接状态
     */
    public boolean isRedisAvailable() {
        try {
            redisTemplate.opsForValue().set("health_check", "ok");
            String result = (String) redisTemplate.opsForValue().get("health_check");
            redisTemplate.delete("health_check");
            return "ok".equals(result);
        } catch (Exception e) {
            log.error("Redis连接检查失败", e);
            return false;
        }
    }
}