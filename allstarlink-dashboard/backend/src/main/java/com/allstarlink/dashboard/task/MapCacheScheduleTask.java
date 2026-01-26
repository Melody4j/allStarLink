package com.allstarlink.dashboard.task;

import com.allstarlink.dashboard.mapper.DimNodesMapper;
import com.allstarlink.dashboard.vo.MapNodeVO;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.concurrent.TimeUnit;

/**
 * 地图缓存定时任务
 * 定时刷新地图节点缓存
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class MapCacheScheduleTask {

    private final RedisTemplate<String, Object> redisTemplate;
    private final DimNodesMapper dimNodesMapper;

    // 缓存键
    private static final String MAP_NODES_CACHE_KEY = "nodes:map:all";

    /**
     * 定时刷新地图节点缓存
     * 每5分钟执行一次
     */
    @Scheduled(fixedRate = 5 * 60 * 1000)
    public void refreshMapNodesCache() {
        log.info("开始定时刷新地图节点缓存");

        try {
            // 从数据库查询所有地图节点
            List<MapNodeVO> nodes = dimNodesMapper.selectAllMapNodes();

            if (nodes == null || nodes.isEmpty()) {
                log.warn("数据库中无地图节点数据");
                return;
            }

            // 更新Redis缓存，设置60分钟过期时间
            redisTemplate.opsForValue().set(MAP_NODES_CACHE_KEY, nodes, 60, TimeUnit.MINUTES);

            log.info("地图节点缓存刷新完成，节点数量: {}", nodes.size());
        } catch (Exception e) {
            log.error("定时刷新地图节点缓存失败", e);
        }
    }

    /**
     * 应用启动时初始化缓存
     * 延迟10秒后执行，确保应用完全启动
     */
    @Scheduled(initialDelay = 10 * 1000, fixedRate = Long.MAX_VALUE)
    public void initMapNodesCache() {
        log.info("应用启动，初始化地图节点缓存");

        try {
            // 检查缓存是否已存在
            Boolean hasKey = redisTemplate.hasKey(MAP_NODES_CACHE_KEY);

            if (Boolean.TRUE.equals(hasKey)) {
                log.info("地图节点缓存已存在，跳过初始化");
                return;
            }

            // 从数据库查询所有地图节点
            List<MapNodeVO> nodes = dimNodesMapper.selectAllMapNodes();

            if (nodes == null || nodes.isEmpty()) {
                log.warn("数据库中无地图节点数据");
                return;
            }

            // 更新Redis缓存，设置60分钟过期时间
            redisTemplate.opsForValue().set(MAP_NODES_CACHE_KEY, nodes, 60, TimeUnit.MINUTES);

            log.info("地图节点缓存初始化完成，节点数量: {}", nodes.size());
        } catch (Exception e) {
            log.error("初始化地图节点缓存失败", e);
        }
    }
}
