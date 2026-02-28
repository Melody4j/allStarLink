package com.allstarlink.dashboard.controller;

import com.allstarlink.dashboard.service.CacheManagerService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.Map;

/**
 * 缓存管理控制器
 * 提供缓存管理和监控的API端点
 */
@RestController
@RequestMapping("/cache")
@RequiredArgsConstructor
@Slf4j
public class CacheController {

    private final CacheManagerService cacheManagerService;

    /**
     * 手动清除所有节点缓存
     */
    @PostMapping("/clear/nodes")
    public ResponseEntity<Map<String, Object>> clearNodeCache() {
        log.info("收到清除节点缓存请求");
        Map<String, Object> result = new HashMap<>();
        return ResponseEntity.ok(result);
    }

    /**
     * 清除指定节点缓存
     */
    @PostMapping("/clear/node/{nodeId}")
    public ResponseEntity<Map<String, Object>> clearSingleNodeCache(@PathVariable Integer nodeId) {
        log.info("收到清除单个节点缓存请求: nodeId={}", nodeId);
        Map<String, Object> result = new HashMap<>();
        return ResponseEntity.ok(result);
    }

    /**
     * 手动清除所有缓存
     */
    @PostMapping("/clear/all")
    public ResponseEntity<Map<String, Object>> clearAllCache() {
        log.info("收到清除所有缓存请求");
        Map<String, Object> result = new HashMap<>();

        try {
            cacheManagerService.clearAllCache();
            result.put("success", true);
            result.put("message", "所有缓存清除成功");
            log.info("所有缓存清除成功");
        } catch (Exception e) {
            result.put("success", false);
            result.put("message", "缓存清除失败: " + e.getMessage());
            log.error("所有缓存清除失败", e);
        }

        return ResponseEntity.ok(result);
    }

    /**
     * 预热缓存
     */
    @PostMapping("/warmup")
    public ResponseEntity<Map<String, Object>> warmUpCache() {
        log.info("收到缓存预热请求");
        Map<String, Object> result = new HashMap<>();

        try {
            cacheManagerService.warmUpCache();
            result.put("success", true);
            result.put("message", "缓存预热成功");
            log.info("缓存预热成功");
        } catch (Exception e) {
            result.put("success", false);
            result.put("message", "缓存预热失败: " + e.getMessage());
            log.error("缓存预热失败", e);
        }

        return ResponseEntity.ok(result);
    }

    /**
     * 获取缓存状态
     */
    @GetMapping("/status")
    public ResponseEntity<Map<String, Object>> getCacheStatus() {
        Map<String, Object> result = new HashMap<>();

        try {
            boolean redisAvailable = cacheManagerService.isRedisAvailable();
            result.put("redisAvailable", redisAvailable);
            result.put("cacheType", "redis");
            result.put("message", redisAvailable ? "Redis缓存正常运行" : "Redis连接异常");

            // 记录缓存统计信息到日志
            cacheManagerService.logCacheStats();

        } catch (Exception e) {
            result.put("redisAvailable", false);
            result.put("message", "缓存状态检查失败: " + e.getMessage());
            log.error("缓存状态检查失败", e);
        }

        return ResponseEntity.ok(result);
    }

    /**
     * 获取缓存统计信息（返回详细数据）
     */
    @GetMapping("/stats")
    public ResponseEntity<Map<String, Object>> getCacheStats() {
        Map<String, Object> result = new HashMap<>();

        try {
            boolean redisAvailable = cacheManagerService.isRedisAvailable();
            result.put("redisAvailable", redisAvailable);

            if (redisAvailable) {
                result.put("success", true);
                result.put("message", "缓存统计信息获取成功");
                // 这里可以添加更详细的缓存统计信息
            } else {
                result.put("success", false);
                result.put("message", "Redis不可用，无法获取统计信息");
            }

        } catch (Exception e) {
            result.put("success", false);
            result.put("message", "缓存统计信息获取失败: " + e.getMessage());
            log.error("获取缓存统计信息失败", e);
        }

        return ResponseEntity.ok(result);
    }
}