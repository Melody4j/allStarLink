package com.allstarlink.dashboard.controller;

import com.allstarlink.dashboard.common.PageResult;
import com.allstarlink.dashboard.common.Result;
import com.allstarlink.dashboard.dto.MapBoundsQueryDTO;
import com.allstarlink.dashboard.dto.PageQueryDTO;
import com.allstarlink.dashboard.service.DimNodesService;
import com.allstarlink.dashboard.vo.MapNodeVO;
import com.allstarlink.dashboard.vo.NodeListVO;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import javax.validation.Valid;
import javax.validation.constraints.NotNull;
import java.util.List;
import java.util.Map;

/**
 * 节点维度表控制器
 * 提供基于数仓维度表dim_nodes的高性能查询API
 *
 * @author AllStarLink Dashboard
 */
@Slf4j
@RestController
@RequestMapping("/api/nodes")
@RequiredArgsConstructor
@Validated
public class DimNodesController {

    private final DimNodesService dimNodesService;

    // ======================= 地图按需加载API =======================


    @GetMapping("/map/bounds")
    public ResponseEntity<Result<List<MapNodeVO>>> getMapNodesByBounds(
            @Valid @ModelAttribute MapBoundsQueryDTO queryDTO) {

        log.info("地图节点查询请求: {}", queryDTO);

        try {
            List<MapNodeVO> nodes = dimNodesService.getMapNodesByBounds(queryDTO);

            if (nodes.isEmpty()) {
                return ResponseEntity.ok(Result.success("查询区域内暂无活跃节点", nodes));
            }

            // 记录查询统计信息
            Long totalCount = dimNodesService.countNodesByBounds(queryDTO);
            String message = String.format("成功查询到 %d 个节点（区域内总计 %d 个）",
                    nodes.size(), totalCount);

            return ResponseEntity.ok(Result.success(message, nodes));
        } catch (Exception e) {
            log.error("地图节点查询失败", e);
            return ResponseEntity.ok(Result.error("地图节点查询失败: " + e.getMessage()));
        }
    }

    @GetMapping("/map/bounds/count")
    public ResponseEntity<Result<Long>> countNodesByBounds(
            @Valid @ModelAttribute MapBoundsQueryDTO queryDTO) {

        log.debug("区域节点数量统计请求: {}", queryDTO);

        try {
            Long count = dimNodesService.countNodesByBounds(queryDTO);
            return ResponseEntity.ok(Result.success("统计完成", count));
        } catch (Exception e) {
            log.error("区域节点统计失败", e);
            return ResponseEntity.ok(Result.error("区域节点统计失败: " + e.getMessage()));
        }
    }

    // ======================= 分页查询API =======================

    @GetMapping("/list")
    public ResponseEntity<Result<PageResult<NodeListVO>>> getNodeListByPage(
            @Valid @ModelAttribute PageQueryDTO queryDTO) {

        log.info("节点分页查询请求: 第{}页, 每页{}条", queryDTO.getCurrent(), queryDTO.getSize());

        try {
            PageResult<NodeListVO> pageResult = dimNodesService.getNodeListByPage(queryDTO);

            String message = String.format("查询成功，共 %d 条记录", pageResult.getTotal());
            return ResponseEntity.ok(Result.success(message, pageResult));
        } catch (Exception e) {
            log.error("节点分页查询失败", e);
            return ResponseEntity.ok(Result.error("节点分页查询失败: " + e.getMessage()));
        }
    }

    // ======================= 节点详情API =======================

    @GetMapping("/{nodeId}")
    public ResponseEntity<Result<NodeListVO>> getNodeById(
            @PathVariable @NotNull Integer nodeId) {

        log.info("节点详情查询: nodeId={}", nodeId);

        try {
            NodeListVO node = dimNodesService.getNodeById(nodeId);

            if (node == null) {
                return ResponseEntity.ok(Result.error("节点不存在: " + nodeId));
            }

            return ResponseEntity.ok(Result.success("查询成功", node));
        } catch (Exception e) {
            log.error("节点详情查询失败: nodeId={}", nodeId, e);
            return ResponseEntity.ok(Result.error("节点详情查询失败: " + e.getMessage()));
        }
    }

    // ======================= 健康检查API =======================

    @GetMapping("/health")
    public ResponseEntity<Result<String>> healthCheck() {
        try {
            // 执行简单的数据库连接测试
            Map<String, Long> globalStats = dimNodesService.getGlobalStats();

            String healthInfo = String.format(
                "节点服务正常运行 - 总节点: %d, 活跃节点: %d",
                globalStats.getOrDefault("totalNodes", 0L),
                globalStats.getOrDefault("activeNodes", 0L)
            );

            return ResponseEntity.ok(Result.success(healthInfo));
        } catch (Exception e) {
            log.error("健康检查失败", e);
            return ResponseEntity.ok(Result.error("服务异常: " + e.getMessage()));
        }
    }
}