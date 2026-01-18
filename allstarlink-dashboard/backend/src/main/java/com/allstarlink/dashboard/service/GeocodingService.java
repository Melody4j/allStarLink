package com.allstarlink.dashboard.service;

import lombok.extern.slf4j.Slf4j;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.util.UriComponentsBuilder;

import java.util.List;
import java.util.Map;

@Service
@Slf4j
public class GeocodingService {

    private final RestTemplate restTemplate = new RestTemplate();
    
    // 高德地图Web服务API密钥（使用与前端相同的密钥）
    private static final String AMAP_API_KEY = "2d608fb0a4f54f0bf39462b10bb7dce3";
    
    // 高德地图地理编码API URL
    private static final String AMAP_GEOCODING_API_URL = "https://restapi.amap.com/v3/geocode/geo";
    
    // 高德地图逆地理编码API URL
    private static final String AMAP_REVERSE_GEOCODING_API_URL = "https://restapi.amap.com/v3/geocode/regeo";
    
    // 根据经纬度获取国家名称
    @Cacheable(value = "geocodingCache", key = "#latitude + ',' + #longitude")
    public String getCountryFromCoordinates(double latitude, double longitude) {
        try {
            // 构建请求URL，使用高德地图逆地理编码API
            // 高德地图的location参数格式为：longitude,latitude
            String locationParam = longitude + "," + latitude;
            String url = UriComponentsBuilder.fromHttpUrl(AMAP_REVERSE_GEOCODING_API_URL)
                    .queryParam("key", AMAP_API_KEY)
                    .queryParam("location", locationParam)
                    .queryParam("output", "json")
                    .queryParam("extensions", "base")
                    .toUriString();
            
            // 调用高德地图API
            Map<String, Object> response = restTemplate.getForObject(url, Map.class);
            
            // 解析结果
            if (response != null) {
                String status = (String) response.get("status");
                if ("1".equals(status)) {
                    Map<String, Object> regeocode = (Map<String, Object>) response.get("regeocode");
                    if (regeocode != null) {
                        Map<String, Object> addressComponent = (Map<String, Object>) regeocode.get("addressComponent");
                        if (addressComponent != null) {
                            String country = (String) addressComponent.get("country");
                            if (country != null && !country.isEmpty()) {
                                log.debug("Coordinates [{}, {}] mapped to country: {}", latitude, longitude, country);
                                return country;
                            }
                        }
                    }
                }
            }
        } catch (Exception e) {
            log.error("Reverse geocoding failed for coordinates [{}, {}]: {}", latitude, longitude, e.getMessage());
        }
        
        log.debug("Could not determine country for coordinates [{}, {}], defaulting to 'other'", latitude, longitude);
        return "other";
    }
}