
package com.allstarlink.dashboard.controller;

import com.allstarlink.dashboard.common.Result;
import com.allstarlink.dashboard.service.NodeCacheService;
import com.allstarlink.dashboard.vo.MapNodeVO;
import com.allstarlink.dashboard.vo.NodeIndexVO;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * 节点缓存控制器
 * 提供基于缓存的节点查询API
 *
 * @author AllStarLink Dashboard
 */
@Slf4j
@RestController
@RequestMapping("/api/nodes/cache")
@RequiredArgsConstructor
public class NodeCacheController {

    private final NodeCacheService nodeCacheService;

    /**
     * 获取全量节点索引
     * 用于低缩放级别的节点抽稀
     */
    @GetMapping("/index")
    public ResponseEntity<Result<List<NodeIndexVO>>> getAllNodesIndex() {
        log.info("获取全量节点索引");

        try {
            List<NodeIndexVO> nodes = nodeCacheService.getAllNodesIndex();

            if (nodes.isEmpty()) {
                return ResponseEntity.ok(Result.success("暂无节点数据", nodes));
            }

            String message = String.format("成功获取全量节点索引，共%d个节点", nodes.size());
            return ResponseEntity.ok(Result.success(message, nodes));
        } catch (Exception e) {
            log.error("获取全量节点索引失败", e);
            return ResponseEntity.ok(Result.error("获取全量节点索引失败: " + e.getMessage()));
        }
    }

    /**
     * 根据缩放级别获取节点
     */
    @GetMapping("/zoom/{zoomLevel}")
    public ResponseEntity<Result<List<MapNodeVO>>> getNodesByZoomLevel(
            @PathVariable Integer zoomLevel) {

        log.info("获取缩放级别{}的节点", zoomLevel);

        try {
            List<MapNodeVO> nodes = nodeCacheService.getNodesByZoomLevel(zoomLevel);

            if (nodes.isEmpty()) {
                return ResponseEntity.ok(Result.success("该缩放级别暂无节点数据", nodes));
            }

            String message = String.format("成功获取缩放级别%d的节点，共%d个", zoomLevel, nodes.size());
            return ResponseEntity.ok(Result.success(message, nodes));
        } catch (Exception e) {
            log.error("获取缩放级别{}的节点失败", zoomLevel, e);
            return ResponseEntity.ok(Result.error("获取节点失败: " + e.getMessage()));
        }
    }

    /**
     * 刷新全量节点缓存
     */
    @PostMapping("/refresh/index")
    public ResponseEntity<Result<String>> refreshAllNodesCache() {
        log.info("刷新全量节点缓存");

        try {
            nodeCacheService.refreshAllNodesCache();
            return ResponseEntity.ok(Result.success("全量节点缓存已刷新"));
        } catch (Exception e) {
            log.error("刷新全量节点缓存失败", e);
            return ResponseEntity.ok(Result.error("刷新缓存失败: " + e.getMessage()));
        }
    }

    /**
     * 刷新指定缩放级别的缓存
     */
    @PostMapping("/refresh/zoom/{zoomLevel}")
    public ResponseEntity<Result<String>> refreshZoomLevelCache(
            @PathVariable Integer zoomLevel) {

        log.info("刷新缩放级别{}的缓存", zoomLevel);

        try {
            nodeCacheService.refreshZoomLevelCache(zoomLevel);
            return ResponseEntity.ok(Result.success("缩放级别" + zoomLevel + "的缓存已刷新"));
        } catch (Exception e) {
            log.error("刷新缩放级别{}的缓存失败", zoomLevel, e);
            return ResponseEntity.ok(Result.error("刷新缓存失败: " + e.getMessage()));
        }
    }

    /**
     * 获取所有地图节点（全量，用于前端地图展示）
     */
    @GetMapping("/map/all")
    public ResponseEntity<Result<List<MapNodeVO>>> getAllMapNodes() {
        log.info("获取所有地图节点");

        try {
            List<MapNodeVO> nodes = nodeCacheService.getAllMapNodes();

            if (nodes.isEmpty()) {
                return ResponseEntity.ok(Result.success("暂无地图节点数据", nodes));
            }

            String message = String.format("成功获取所有地图节点，共%d个", nodes.size());
            return ResponseEntity.ok(Result.success(message, nodes));
        } catch (Exception e) {
            log.error("获取所有地图节点失败", e);
            return ResponseEntity.ok(Result.error("获取地图节点失败: " + e.getMessage()));
        }
    }
}
