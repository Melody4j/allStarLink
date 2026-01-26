
package com.allstarlink.dashboard.service.impl;

import com.allstarlink.dashboard.dto.MapBoundsQueryDTO;
import com.allstarlink.dashboard.mapper.DimNodesMapper;
import com.allstarlink.dashboard.service.NodeCacheService;
import com.allstarlink.dashboard.vo.MapNodeVO;
import com.allstarlink.dashboard.vo.NodeIndexVO;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.concurrent.TimeUnit;

/**
 * 节点缓存服务实现
 * 实现分级缓存策略，降低数据库查询压力
 *
 * @author AllStarLink Dashboard
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class NodeCacheServiceImpl implements NodeCacheService {

    private final RedisTemplate<String, Object> redisTemplate;
    private final DimNodesMapper dimNodesMapper;

    // 缓存键前缀
    private static final String NODE_INDEX_CACHE_KEY = "nodes:index:all";
    private static final String NODE_ZOOM_CACHE_PREFIX = "nodes:zoom:";

    // 缓存过期时间（分钟）
    private static final int INDEX_CACHE_TTL = 30;  // 全量索引缓存30分钟
    private static final int LOW_ZOOM_TTL = 30;    // 低缩放缓存30分钟
    private static final int MID_ZOOM_TTL = 20;    // 中缩放缓存20分钟
    private static final int HIGH_ZOOM_TTL = 10;   // 高缩放缓存10分钟

    @Override
    public List<NodeIndexVO> getAllNodesIndex() {
        String cacheKey = NODE_INDEX_CACHE_KEY;

        try {
            // 尝试从缓存获取
            @SuppressWarnings("unchecked")
            List<NodeIndexVO> cached = (List<NodeIndexVO>) redisTemplate.opsForValue().get(cacheKey);

            if (cached != null && !cached.isEmpty()) {
                log.debug("从缓存获取全量节点索引，数量: {}", cached.size());
                return cached;
            }

            // 从数据库查询全量节点索引（仅必要字段）
            log.info("从数据库加载全量节点索引");
            List<NodeIndexVO> nodes = dimNodesMapper.selectAllNodesIndex();

            // 缓存到Redis
            redisTemplate.opsForValue().set(cacheKey, nodes, INDEX_CACHE_TTL, TimeUnit.MINUTES);
            log.info("全量节点索引已缓存，数量: {}, TTL: {}分钟", nodes.size(), INDEX_CACHE_TTL);

            return nodes;
        } catch (Exception e) {
            log.error("获取全量节点索引失败", e);
            return new java.util.ArrayList<>();
        }
    }

    @Override
    public List<MapNodeVO> getNodesByZoomLevel(int zoomLevel) {
        // 根据缩放级别计算缓存键
        int cacheLevel = calculateCacheLevel(zoomLevel);
        String cacheKey = NODE_ZOOM_CACHE_PREFIX + cacheLevel;

        try {
            // 尝试从缓存获取
            @SuppressWarnings("unchecked")
            List<MapNodeVO> cached = (List<MapNodeVO>) redisTemplate.opsForValue().get(cacheKey);

            if (cached != null && !cached.isEmpty()) {
                log.debug("从缓存获取缩放级别{}的节点，数量: {}", cacheLevel, cached.size());
                return cached;
            }

            // 从数据库查询指定缩放级别的节点
            log.info("从数据库加载缩放级别{}的节点", cacheLevel);
            List<MapNodeVO> nodes = dimNodesMapper.selectNodesByZoomLevel(cacheLevel);

            // 计算缓存过期时间
            long ttl = calculateTTLByZoom(zoomLevel);

            // 缓存到Redis
            redisTemplate.opsForValue().set(cacheKey, nodes, ttl, TimeUnit.MINUTES);
            log.info("缩放级别{}的节点已缓存，数量: {}, TTL: {}分钟", cacheLevel, nodes.size(), ttl);

            return nodes;
        } catch (Exception e) {
            log.error("获取缩放级别{}的节点失败", zoomLevel, e);
            return new java.util.ArrayList<>();
        }
    }

    @Override
    public List<MapNodeVO> getNodesByBounds(Double minLat, Double maxLat, Double minLng, Double maxLng, int zoomLevel) {
        // 高缩放级别（> 8）：直接查询数据库，不缓存
        if (zoomLevel > 8) {
            log.debug("高缩放级别{}，直接查询数据库", zoomLevel);
            return dimNodesMapper.selectMapNodesByBounds(
                new MapBoundsQueryDTO(minLat, maxLat, minLng, maxLng, zoomLevel)
            );
        }
            
        List<MapNodeVO> cachedNodes = getNodesByZoomLevel(zoomLevel);
        List<MapNodeVO> result = new java.util.ArrayList<>();
        for (MapNodeVO node : cachedNodes) {
            if (node.getLatitude() >= minLat &&
                node.getLatitude() <= maxLat &&
                node.getLongitude() >= minLng &&
                node.getLongitude() <= maxLng) {
                result.add(node);
            }
        }
        return result;
    }

    @Override
    public void refreshAllNodesCache() {
        try {
            log.info("刷新全量节点缓存");
            redisTemplate.delete(NODE_INDEX_CACHE_KEY);
            log.info("全量节点缓存已刷新");
        } catch (Exception e) {
            log.error("刷新全量节点缓存失败", e);
        }
    }

    @Override
    public void refreshZoomLevelCache(int zoomLevel) {
        try {
            int cacheLevel = calculateCacheLevel(zoomLevel);
            String cacheKey = NODE_ZOOM_CACHE_PREFIX + cacheLevel;
            log.info("刷新缩放级别{}的缓存", cacheLevel);
            redisTemplate.delete(cacheKey);
            log.info("缩放级别{}的缓存已刷新", cacheLevel);
        } catch (Exception e) {
            log.error("刷新缩放级别{}的缓存失败", zoomLevel, e);
        }
    }

    /**
     * 计算缓存级别
     * 将连续的缩放级别映射到离散的缓存级别
     */
    private int calculateCacheLevel(int zoomLevel) {
        if (zoomLevel <= 4) return 4;
        if (zoomLevel <= 6) return 6;
        if (zoomLevel <= 8) return 8;
        return 10;
    }

    /**
     * 根据缩放级别计算缓存过期时间
     */
    private long calculateTTLByZoom(int zoomLevel) {
        if (zoomLevel <= 4) return LOW_ZOOM_TTL;
        if (zoomLevel <= 8) return MID_ZOOM_TTL;
        return HIGH_ZOOM_TTL;
    }

    @Override
    public List<MapNodeVO> getAllMapNodes() {
        String cacheKey = "nodes:map:all";

        try {
            // 尝试从缓存获取
            @SuppressWarnings("unchecked")
            List<MapNodeVO> cached = (List<MapNodeVO>) redisTemplate.opsForValue().get(cacheKey);

            if (cached != null && !cached.isEmpty()) {
                log.debug("从缓存获取所有地图节点，数量: {}", cached.size());
                return cached;
            }

            // 从数据库查询所有地图节点
            log.info("从数据库加载所有地图节点");
            List<MapNodeVO> nodes = dimNodesMapper.selectAllMapNodes();

            // 缓存到Redis，设置较长的过期时间（1小时）
            redisTemplate.opsForValue().set(cacheKey, nodes, 60, TimeUnit.MINUTES);
            log.info("所有地图节点已缓存，数量: {}, TTL: 60分钟", nodes.size());

            return nodes;
        } catch (Exception e) {
            log.error("获取所有地图节点失败", e);
            return new java.util.ArrayList<>();
        }
    }
}
