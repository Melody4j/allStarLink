package com.allstarlink.dashboard.service.impl;

import com.allstarlink.dashboard.common.PageResult;
import com.allstarlink.dashboard.dto.MapBoundsQueryDTO;
import com.allstarlink.dashboard.dto.PageQueryDTO;
import com.allstarlink.dashboard.mapper.DimNodesMapper;
import com.allstarlink.dashboard.service.DimNodesService;
import com.allstarlink.dashboard.vo.DistributionStatsVO;
import com.allstarlink.dashboard.vo.MapNodeVO;
import com.allstarlink.dashboard.vo.NodeListVO;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;
import org.springframework.util.CollectionUtils;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * 节点维度表业务服务实现类
 * 基于数仓维度表dim_nodes的高性能查询和缓存优化
 *
 * @author AllStarLink Dashboard
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class DimNodesServiceImpl implements DimNodesService {

    private final DimNodesMapper dimNodesMapper;

    // ======================= 地图按需加载相关方法 =======================

    @Override
    public List<MapNodeVO> getMapNodesByBounds(MapBoundsQueryDTO queryDTO) {
        log.debug("查询地图节点: 边界[{},{},{},{}], 缩放级别: {}",
                queryDTO.getMinLng(), queryDTO.getMaxLng(),
                queryDTO.getMinLat(), queryDTO.getMaxLat(), queryDTO.getZoomLevel());

        // 参数校验
        if (!queryDTO.isValidBounds()) {
            log.warn("无效的地理边界参数: {}", queryDTO);
            return Collections.emptyList();
        }

        // 大区域查询保护，避免查询范围过大
        Double area = queryDTO.calculateArea();
        if (area > 10000) { // 经纬度面积 > 10000 的大范围查询
            log.warn("查询区域过大: {} 平方度，已限制返回数量", area);
            // 可以在这里进一步限制查询条件或抽稀策略
        }

        try {
            List<MapNodeVO> nodes = dimNodesMapper.selectMapNodesByBounds(queryDTO);
            log.debug("查询到 {} 个地图节点", nodes.size());
            return nodes;
        } catch (Exception e) {
            log.error("查询地图节点失败", e);
            return Collections.emptyList();
        }
    }

    @Override
    public Long countNodesByBounds(MapBoundsQueryDTO queryDTO) {
        if (!queryDTO.isValidBounds()) {
            return 0L;
        }

        try {
            return dimNodesMapper.countNodesByBounds(queryDTO);
        } catch (Exception e) {
            log.error("统计区域节点数量失败", e);
            return 0L;
        }
    }

    // ======================= 分布统计相关方法 =======================

    @Override
    // @Cacheable(value = "nodeStats", key = "'distribution_continent'", unless = "#result.isEmpty()")
    public List<DistributionStatsVO> getDistributionByContinent() {
        log.debug("查询大洲节点分布统计");

        try {
            List<DistributionStatsVO> stats = dimNodesMapper.selectDistributionByContinent();

            // 计算各大洲占总体的百分比
            long totalGlobal = stats.stream().mapToLong(stat -> stat.getTotalCount().longValue()).sum();
            stats.forEach(stat -> {
                BigDecimal percentage = BigDecimal.valueOf(stat.getTotalCount())
                        .multiply(BigDecimal.valueOf(100))
                        .divide(BigDecimal.valueOf(totalGlobal), 2, RoundingMode.HALF_UP);
                stat.setPercentage(percentage);
            });

            log.debug("查询到 {} 个大洲的分布统计", stats.size());
            return stats;
        } catch (Exception e) {
            log.error("查询大洲分布统计失败", e);
            return Collections.emptyList();
        }
    }

    @Override
    // @Cacheable(value = "nodeStats", key = "'distribution_country'", unless = "#result.isEmpty()")
    public List<DistributionStatsVO> getDistributionByCountry() {
        log.debug("查询国家节点分布统计");

        try {
            List<DistributionStatsVO> stats = dimNodesMapper.selectDistributionByCountry();

            // 计算各国占总体的百分比
            Map<String, Long> globalStats = getGlobalStats();
            long totalGlobal = globalStats.getOrDefault("totalNodes", 1L);
            stats.forEach(stat -> {
                BigDecimal percentage = BigDecimal.valueOf(stat.getTotalCount())
                        .multiply(BigDecimal.valueOf(100))
                        .divide(BigDecimal.valueOf(totalGlobal), 2, RoundingMode.HALF_UP);
                stat.setPercentage(percentage);
            });

            log.debug("查询到 {} 个国家的分布统计", stats.size());
            return stats;
        } catch (Exception e) {
            log.error("查询国家分布统计失败", e);
            return Collections.emptyList();
        }
    }

    @Override
    public List<DistributionStatsVO> getDistributionByDimension(String dimension) {
        if ("continent".equals(dimension)) {
            return getDistributionByContinent();
        } else if ("country".equals(dimension)) {
            return getDistributionByCountry();
        } else {
            log.warn("不支持的统计维度: {}", dimension);
            return Collections.emptyList();
        }
    }

    @Override
    // @Cacheable(value = "nodeStats", key = "'global_stats'")
    public Map<String, Long> getGlobalStats() {
        log.debug("查询全球节点统计信息");

        try {
            Map<String, Long> stats = dimNodesMapper.selectGlobalStats();
            log.debug("全球统计: 总节点数={}, 活跃节点数={}",
                    stats.get("totalNodes"), stats.get("activeNodes"));
            return stats;
        } catch (Exception e) {
            log.error("查询全球统计失败", e);
            Map<String, Long> emptyStats = new java.util.HashMap<>();
            emptyStats.put("totalNodes", 0L);
            emptyStats.put("activeNodes", 0L);
            return emptyStats;
        }
    }

    // ======================= 分页查询相关方法 =======================

    @Override
    public PageResult<NodeListVO> getNodeListByPage(PageQueryDTO queryDTO) {
        log.debug("分页查询节点列表: 第{}页, 每页{}条", queryDTO.getCurrent(), queryDTO.getSize());

        try {
            // 查询分页数据
            List<NodeListVO> records = dimNodesMapper.selectNodeListByPage(queryDTO);

            // 查询总数
            Long total = dimNodesMapper.countNodeListByPage(queryDTO);

            log.debug("查询到 {} 条记录，总数 {}", records.size(), total);

            return PageResult.of(queryDTO.getCurrent(), queryDTO.getSize(), total, records);
        } catch (Exception e) {
            log.error("分页查询节点列表失败", e);
            return PageResult.of(queryDTO.getCurrent(), queryDTO.getSize(), 0L, Collections.emptyList());
        }
    }

    // ======================= 基础数据操作 =======================

    @Override
    public NodeListVO getNodeById(Integer nodeId) {
        if (nodeId == null) {
            return null;
        }

        log.debug("查询节点详情: nodeId={}", nodeId);

        try {
            // 构造单条查询的PageQueryDTO
            PageQueryDTO queryDTO = new PageQueryDTO();
            queryDTO.setCurrent(1L);
            queryDTO.setSize(1L);

            // 这里可以通过添加一个专门的单条查询方法来优化
            // 暂时使用分页查询方法
            List<NodeListVO> nodes = dimNodesMapper.selectNodeListByPage(queryDTO);

            return nodes.stream()
                    .filter(node -> nodeId.equals(node.getNodeId()))
                    .findFirst()
                    .orElse(null);
        } catch (Exception e) {
            log.error("查询节点详情失败: nodeId={}", nodeId, e);
            return null;
        }
    }

    @Override
    @Cacheable(value = "nodeActivity", key = "#nodeIds.hashCode()", unless = "#result.isEmpty()")
    public Map<Integer, Double> getActivityRates24h(List<Integer> nodeIds) {
        if (CollectionUtils.isEmpty(nodeIds)) {
            return Collections.emptyMap();
        }

        log.debug("查询节点24小时活跃率: {} 个节点", nodeIds.size());

        try {
            Map<Integer, BigDecimal> rates = dimNodesMapper.selectActivityRates24h(nodeIds);

            // 转换 BigDecimal 为 Double
            return rates.entrySet().stream()
                    .collect(Collectors.toMap(
                            Map.Entry::getKey,
                            entry -> entry.getValue().doubleValue()
                    ));
        } catch (Exception e) {
            log.error("查询节点活跃率失败", e);
            return Collections.emptyMap();
        }
    }
}