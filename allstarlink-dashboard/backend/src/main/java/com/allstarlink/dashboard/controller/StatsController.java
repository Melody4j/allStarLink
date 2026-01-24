package com.allstarlink.dashboard.controller;

import com.allstarlink.dashboard.common.Result;
import com.allstarlink.dashboard.service.DimNodesService;
import com.allstarlink.dashboard.vo.DistributionStatsVO;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import javax.validation.constraints.Pattern;
import java.util.List;
import java.util.Map;

/**
 * 统计分析控制器
 * 提供全球节点分布统计和多维度数据分析API
 *
 * @author AllStarLink Dashboard
 */
@Slf4j
@RestController
@RequestMapping("/api/stats")
@RequiredArgsConstructor
public class StatsController {

    private final DimNodesService dimNodesService;

    // ======================= 分布统计API =======================

    @GetMapping("/distribution")
    public ResponseEntity<Result<List<DistributionStatsVO>>> getDistribution(
            @RequestParam
            @Pattern(regexp = "^(continent|country)$",
                    message = "统计维度必须为 'continent' 或 'country'")
            String dimension) {

        log.info("获取节点分布统计: dimension={}", dimension);

        try {
            List<DistributionStatsVO> stats = dimNodesService.getDistributionByDimension(dimension);

            if (stats.isEmpty()) {
                return ResponseEntity.ok(Result.success("暂无统计数据", stats));
            }

            String message = String.format("成功获取%s分布统计，共%d个%s",
                    "continent".equals(dimension) ? "大洲" : "国家",
                    stats.size(),
                    "continent".equals(dimension) ? "大洲" : "国家");

            return ResponseEntity.ok(Result.success(message, stats));
        } catch (Exception e) {
            log.error("获取分布统计失败: dimension={}", dimension, e);
            return ResponseEntity.ok(Result.error("获取分布统计失败: " + e.getMessage()));
        }
    }

    @GetMapping("/distribution/continent")
    public ResponseEntity<Result<List<DistributionStatsVO>>> getDistributionByContinent() {
        log.info("获取大洲节点分布统计");

        try {
            List<DistributionStatsVO> stats = dimNodesService.getDistributionByContinent();

            String message = String.format("成功获取大洲分布统计，共%d个大洲", stats.size());
            return ResponseEntity.ok(Result.success(message, stats));
        } catch (Exception e) {
            log.error("获取大洲分布统计失败", e);
            return ResponseEntity.ok(Result.error("获取大洲分布统计失败: " + e.getMessage()));
        }
    }

    @GetMapping("/distribution/country")
    public ResponseEntity<Result<List<DistributionStatsVO>>> getDistributionByCountry() {
        log.info("获取国家节点分布统计");

        try {
            List<DistributionStatsVO> stats = dimNodesService.getDistributionByCountry();

            String message = String.format("成功获取国家分布统计，共%d个国家", stats.size());
            return ResponseEntity.ok(Result.success(message, stats));
        } catch (Exception e) {
            log.error("获取国家分布统计失败", e);
            return ResponseEntity.ok(Result.error("获取国家分布统计失败: " + e.getMessage()));
        }
    }

    // ======================= 全局统计API =======================

    @GetMapping("/global")
    public ResponseEntity<Result<Map<String, Long>>> getGlobalStats() {
        log.info("获取全球节点统计");

        try {
            Map<String, Long> stats = dimNodesService.getGlobalStats();

            long totalNodes = stats.getOrDefault("totalNodes", 0L);
            long activeNodes = stats.getOrDefault("activeNodes", 0L);

            String message = String.format("全球统计: 总节点 %d 个，活跃节点 %d 个",
                    totalNodes, activeNodes);

            return ResponseEntity.ok(Result.success(message, stats));
        } catch (Exception e) {
            log.error("获取全球统计失败", e);
            return ResponseEntity.ok(Result.error("获取全球统计失败: " + e.getMessage()));
        }
    }

    // ======================= 数据概览API =======================

    @GetMapping("/overview")
    public ResponseEntity<Result<Map<String, Object>>> getStatsOverview() {
        log.info("获取数据统计概览");

        try {
            // 获取全球统计
            Map<String, Long> globalStats = dimNodesService.getGlobalStats();

            // 获取大洲分布（用于计算覆盖范围）
            List<DistributionStatsVO> continentStats = dimNodesService.getDistributionByContinent();
            long activeContinents = continentStats.stream()
                    .mapToLong(stat -> stat.getActiveCount() != null && stat.getActiveCount() > 0 ? 1 : 0)
                    .sum();

            // 获取国家分布（用于计算覆盖范围）
            List<DistributionStatsVO> countryStats = dimNodesService.getDistributionByCountry();
            long activeCountries = countryStats.stream()
                    .mapToLong(stat -> stat.getActiveCount() != null && stat.getActiveCount() > 0 ? 1 : 0)
                    .sum();

            // 计算全球活跃率
            long totalNodes = ((Number) globalStats.getOrDefault("totalNodes", 0L)).longValue();
            long activeNodes = ((Number) globalStats.getOrDefault("activeNodes", 0L)).longValue();
            double globalActiveRate = totalNodes > 0 ? (activeNodes * 100.0 / totalNodes) : 0.0;

            Map<String, Object> overview = new java.util.HashMap<>();
            overview.put("totalNodes", totalNodes);
            overview.put("activeNodes", activeNodes);
            overview.put("globalActiveRate", Math.round(globalActiveRate * 100.0) / 100.0);
            overview.put("activeContinents", activeContinents);
            overview.put("activeCountries", activeCountries);
            overview.put("totalContinents", continentStats.size());
            overview.put("totalCountries", countryStats.size());

            return ResponseEntity.ok(Result.success("概览数据获取成功", overview));
        } catch (Exception e) {
            log.error("获取统计概览失败", e);
            return ResponseEntity.ok(Result.error("获取统计概览失败: " + e.getMessage()));
        }
    }
}