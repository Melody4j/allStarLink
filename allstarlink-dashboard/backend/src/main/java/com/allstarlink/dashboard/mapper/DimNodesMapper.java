package com.allstarlink.dashboard.mapper;

import com.allstarlink.dashboard.dto.MapBoundsQueryDTO;
import com.allstarlink.dashboard.dto.PageQueryDTO;
import com.allstarlink.dashboard.entity.DimNodes;
import com.allstarlink.dashboard.vo.DistributionStatsVO;
import com.allstarlink.dashboard.vo.MapNodeVO;
import com.allstarlink.dashboard.vo.NodeListVO;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * 节点维度表 Mapper 接口
 * 继承 MyBatis Plus 的 BaseMapper，提供基础 CRUD 操作
 */
@Mapper
public interface DimNodesMapper extends BaseMapper<DimNodes> {

    /**
     * 根据节点ID获取节点维度信息
     * @param nodeId 节点ID
     * @return 节点维度信息
     */
    Optional<DimNodes> selectByNodeId(@Param("nodeId") Integer nodeId);

    /**
     * 获取所有活跃节点
     * @return 活跃节点列表
     */
    List<DimNodes> selectActiveNodes();

    /**
     * 根据组织类型查询节点
     * @param affiliationType 组织类型：Personal/Club/System
     * @return 节点列表
     */
    List<DimNodes> selectByAffiliationType(@Param("affiliationType") String affiliationType);

    /**
     * 根据国家查询节点
     * @param country 国家名称
     * @return 节点列表
     */
    List<DimNodes> selectByCountry(@Param("country") String country);

    /**
     * 根据节点等级查询节点
     * @param nodeRank 节点等级：Core/Active/Transient
     * @return 节点列表
     */
    List<DimNodes> selectByNodeRank(@Param("nodeRank") String nodeRank);

    /**
     * 根据移动属性查询节点
     * @param mobilityType 移动属性：Fixed/Mobile
     * @return 节点列表
     */
    List<DimNodes> selectByMobilityType(@Param("mobilityType") String mobilityType);

    /**
     * 根据地理范围查询节点
     * @param minLat 最小纬度
     * @param maxLat 最大纬度
     * @param minLon 最小经度
     * @param maxLon 最大经度
     * @return 节点列表
     */
    List<DimNodes> selectByGeoBounds(@Param("minLat") Double minLat,
                                     @Param("maxLat") Double maxLat,
                                     @Param("minLon") Double minLon,
                                     @Param("maxLon") Double maxLon);

    /**
     * 查询移动节点
     * @return 移动节点列表
     */
    List<DimNodes> selectMobileNodes();

    /**
     * 查询指定时间后首次入网的节点
     * @param firstSeenAfter 时间阈值
     * @return 节点列表
     */
    List<DimNodes> selectNodesFirstSeenAfter(@Param("firstSeenAfter") LocalDateTime firstSeenAfter);

    /**
     * 统计活跃节点数量
     * @return 活跃节点数量
     */
    long countActiveNodes();

    /**
     * 根据组织类型统计节点数量
     * @param affiliationType 组织类型
     * @return 节点数量
     */
    long countByAffiliationType(@Param("affiliationType") String affiliationType);

    /**
     * 根据国家统计节点数量
     * @param country 国家名称
     * @return 节点数量
     */
    long countByCountry(@Param("country") String country);

    /**
     * 统计移动节点数量
     * @return 移动节点数量
     */
    long countMobileNodes();

    // ======================= 地图按需加载相关方法 =======================

    /**
     * 根据地理边界查询地图节点信息（性能优化版本）
     * 仅返回地图渲染必要字段，支持缩放级别抽稀
     *
     * @param queryDTO 地图区域查询参数
     * @return 地图节点列表
     */
    List<MapNodeVO> selectMapNodesByBounds(@Param("query") MapBoundsQueryDTO queryDTO);

    /**
     * 根据地理边界统计节点数量
     *
     * @param queryDTO 地图区域查询参数
     * @return 节点总数
     */
    Long countNodesByBounds(@Param("query") MapBoundsQueryDTO queryDTO);

    // ======================= 分布统计相关方法 =======================

    /**
     * 按大洲统计节点分布
     *
     * @return 大洲分布统计列表
     */
    List<DistributionStatsVO> selectDistributionByContinent();

    /**
     * 按国家统计节点分布
     *
     * @return 国家分布统计列表
     */
    List<DistributionStatsVO> selectDistributionByCountry();

    /**
     * 获取全球节点总体统计信息
     *
     * @return 包含总数和活跃数的Map
     */
    Map<String, Long> selectGlobalStats();

    // ======================= 分页查询相关方法 =======================

    /**
     * 分页查询节点列表（包含24小时活跃率计算）
     *
     * @param queryDTO 分页查询参数
     * @return 节点列表
     */
    List<NodeListVO> selectNodeListByPage(@Param("query") PageQueryDTO queryDTO);

    /**
     * 统计分页查询总数
     *
     * @param queryDTO 分页查询参数
     * @return 总记录数
     */
    Long countNodeListByPage(@Param("query") PageQueryDTO queryDTO);

    /**
     * 计算节点24小时活跃率
     * 通过关联dwd_node_events_fact表计算
     *
     * @param nodeIds 节点ID列表
     * @return 节点活跃率Map (key: nodeId, value: activityRate)
     */
    Map<Integer, BigDecimal> selectActivityRates24h(@Param("nodeIds") List<Integer> nodeIds);
}