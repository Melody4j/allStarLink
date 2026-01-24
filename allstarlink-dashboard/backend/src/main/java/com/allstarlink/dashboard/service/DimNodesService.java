package com.allstarlink.dashboard.service;

import com.allstarlink.dashboard.common.PageResult;
import com.allstarlink.dashboard.dto.MapBoundsQueryDTO;
import com.allstarlink.dashboard.dto.PageQueryDTO;
import com.allstarlink.dashboard.vo.DistributionStatsVO;
import com.allstarlink.dashboard.vo.MapNodeVO;
import com.allstarlink.dashboard.vo.NodeListVO;

import java.util.List;
import java.util.Map;

/**
 * 节点维度表业务服务接口
 * 基于数仓维度表dim_nodes的业务逻辑封装
 *
 * @author AllStarLink Dashboard
 */
public interface DimNodesService {

    // ======================= 地图按需加载相关方法 =======================

    /**
     * 根据地理边界查询地图节点信息
     * 高性能地图可视区域按需加载，支持缩放级别抽稀优化
     *
     * @param queryDTO 地图区域查询参数
     * @return 地图节点列表
     */
    List<MapNodeVO> getMapNodesByBounds(MapBoundsQueryDTO queryDTO);

    /**
     * 统计地理边界内的节点数量
     *
     * @param queryDTO 地图区域查询参数
     * @return 节点总数
     */
    Long countNodesByBounds(MapBoundsQueryDTO queryDTO);

    // ======================= 分布统计相关方法 =======================

    /**
     * 获取全球节点分布统计（按大洲）
     * 用于饼图数据展示
     *
     * @return 大洲分布统计列表，按节点数量降序排列
     */
    List<DistributionStatsVO> getDistributionByContinent();

    /**
     * 获取全球节点分布统计（按国家）
     * 用于饼图数据展示，返回前50个国家
     *
     * @return 国家分布统计列表，按节点数量降序排列
     */
    List<DistributionStatsVO> getDistributionByCountry();

    /**
     * 获取指定维度的节点分布统计
     *
     * @param dimension 统计维度：continent 或 country
     * @return 分布统计列表
     */
    List<DistributionStatsVO> getDistributionByDimension(String dimension);

    /**
     * 获取全球节点总体统计信息
     *
     * @return 包含总数和活跃数的Map
     */
    Map<String, Long> getGlobalStats();

    // ======================= 分页查询相关方法 =======================

    /**
     * 分页查询节点列表
     * 包含24小时活跃率计算和多维度筛选
     *
     * @param queryDTO 分页查询参数
     * @return 分页结果
     */
    PageResult<NodeListVO> getNodeListByPage(PageQueryDTO queryDTO);

    // ======================= 基础数据操作 =======================

    /**
     * 根据节点ID获取节点详细信息
     *
     * @param nodeId 节点ID
     * @return 节点信息，如果不存在则返回null
     */
    NodeListVO getNodeById(Integer nodeId);

    /**
     * 批量获取节点的24小时活跃率
     *
     * @param nodeIds 节点ID列表
     * @return 节点活跃率Map (key: nodeId, value: activityRate)
     */
    Map<Integer, Double> getActivityRates24h(List<Integer> nodeIds);
}