
package com.allstarlink.dashboard.service;

import com.allstarlink.dashboard.vo.MapNodeVO;
import com.allstarlink.dashboard.vo.NodeIndexVO;

import java.util.List;

/**
 * 节点缓存服务
 * 提供分级缓存策略，降低数据库查询压力
 *
 * @author AllStarLink Dashboard
 */
public interface NodeCacheService {

    /**
     * 获取全量节点索引（轻量级，仅包含ID和位置）
     * 用于低缩放级别的节点抽稀
     *
     * @return 节点索引列表
     */
    List<NodeIndexVO> getAllNodesIndex();

    /**
     * 获取指定缩放级别的节点
     * 根据缩放级别返回不同密度的节点数据
     *
     * @param zoomLevel 缩放级别
     * @return 节点列表
     */
    List<MapNodeVO> getNodesByZoomLevel(int zoomLevel);

    /**
     * 获取指定区域的节点
     * 用于高缩放级别的按需加载
     *
     * @param minLat 最小纬度
     * @param maxLat 最大纬度
     * @param minLng 最小经度
     * @param maxLng 最大经度
     * @param zoomLevel 缩放级别
     * @return 节点列表
     */
    List<MapNodeVO> getNodesByBounds(Double minLat, Double maxLat, Double minLng, Double maxLng, int zoomLevel);

    /**
     * 刷新全量节点缓存
     * 用于数据更新时主动刷新缓存
     */
    void refreshAllNodesCache();

    /**
     * 刷新指定缩放级别的缓存
     *
     * @param zoomLevel 缩放级别
     */
    void refreshZoomLevelCache(int zoomLevel);

    /**
     * 获取所有地图节点（全量，用于前端地图展示）
     * 从Redis缓存中获取，如果缓存不存在则从数据库加载
     *
     * @return 所有地图节点列表
     */
    List<MapNodeVO> getAllMapNodes();
}
