"""
Geospatial metrics analysis for sustainability projects.
Analyzes coordinates to generate ecological sensitivity scores and recommendations.
"""

import pandas as pd
import json
import math
from pathlib import Path
from typing import Dict, List, Tuple, Optional

class GeospatialMetricsAnalyzer:
    """
    Analyzes project locations based on latitude/longitude coordinates.
    Generates ecological sensitivity scores and improvement metrics.
    """
    
    def __init__(self):
        """Initialize the analyzer with geospatial datasets."""
        self.data_dir = Path(__file__).parent.parent.parent / "Data"
        
        # Load datasets
        self.esa_data = self._load_csv("environmentally_significant_areas_toronto.csv")
        self.green_spaces_data = self._load_csv("green_spaces_toronto.csv")
        self.native_lands_data = self._load_csv("first_nations_canada.csv")
        
    def _load_csv(self, filename: str) -> Optional[pd.DataFrame]:
        """Load CSV file from Data directory."""
        try:
            filepath = self.data_dir / filename
            return pd.read_csv(filepath)
        except Exception as e:
            print(f"Warning: Could not load {filename}: {e}")
            return None
    
    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate distance between two coordinates using Haversine formula.
        Returns distance in kilometers.
        """
        R = 6371  # Earth's radius in km
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = math.sin(delta_lat/2) * math.sin(delta_lat/2) + \
            math.cos(lat1_rad) * math.cos(lat2_rad) * \
            math.sin(delta_lon/2) * math.sin(delta_lon/2)
        
        c = 2 * math.asin(math.sqrt(a))
        return R * c
    
    def find_nearest_features(self, latitude: float, longitude: float, 
                             df: pd.DataFrame, lat_col: str, lon_col: str, 
                             radius_km: float = 1.0) -> List[Dict]:
        """Find features within a radius of the given coordinates."""
        if df is None or df.empty:
            return []
        
        features = []
        
        for idx, row in df.iterrows():
            try:
                # Handle missing coordinates
                if pd.isna(row[lat_col]) or pd.isna(row[lon_col]):
                    continue
                
                distance = self.calculate_distance(
                    latitude, longitude,
                    float(row[lat_col]), float(row[lon_col])
                )
                
                if distance <= radius_km:
                    features.append({
                        'distance_km': round(distance, 3),
                        'feature': row.to_dict()
                    })
            except:
                continue
        
        # Sort by distance
        features.sort(key=lambda x: x['distance_km'])
        return features
    
    def calculate_ecological_sensitivity_score(self, latitude: float, longitude: float) -> Dict:
        """
        Calculate ecological sensitivity score based on location.
        
        Scoring criteria (30 points total):
        - ESA Proximity (10 points): d_min = 1km
        - Green Space Proximity (10 points): d_min = 0.3km  
        - Street Trees (10 points): n_min = 3 trees in 1km radius
        
        Returns:
            Dictionary with:
            - total_score: 0-30
            - esa_score: 0-10
            - green_space_score: 0-10
            - recommendations: List of improvement areas
        """
        
        # ESA Score (0-10)
        esa_features = self.find_nearest_features(
            latitude, longitude, self.esa_data, 
            'LATITUDE', 'LONGITUDE', radius_km=2.0
        )
        
        esa_distance = esa_features[0]['distance_km'] if esa_features else 2.0
        esa_d_min = 1.0
        esa_score = max(0, 10 - 10 * (1 - min(esa_distance, esa_d_min) / esa_d_min))
        
        # Green Space Score (0-10)
        green_features = self.find_nearest_features(
            latitude, longitude, self.green_spaces_data,
            'LATITUDE', 'LONGITUDE', radius_km=0.5
        )
        
        green_distance = green_features[0]['distance_km'] if green_features else 0.5
        green_d_min = 0.3  # 300 metres
        green_score = max(0, 10 - 10 * (1 - min(green_distance, green_d_min) / green_d_min))
        
        # Tree Score (0-10) - placeholder for future street tree data integration
        tree_score = 5  # Default middle score until tree inventory data is available
        
        total_score = round(esa_score + green_score + tree_score, 2)
        
        # Generate recommendations based on scores
        recommendations = self._generate_recommendations(
            esa_score, green_score, tree_score,
            esa_distance, green_distance, esa_features, green_features
        )
        
        return {
            'total_score': total_score,
            'esa_score': round(esa_score, 2),
            'esa_distance_km': esa_distance,
            'nearest_esa': esa_features[0]['feature']['ESA_NAME'] if esa_features else None,
            'green_space_score': round(green_score, 2),
            'green_distance_km': green_distance,
            'nearest_green_space': green_features[0]['feature'].get('AREA_NAME') if green_features else None,
            'tree_score': round(tree_score, 2),
            'recommendations': recommendations,
            'metrics': {
                'canopy_cover_target': '30%',
                'trees_per_resident': 'at least 3',
                'distance_to_park': '300m',
                'esa_proximity': f'{esa_distance}km'
            }
        }
    
    def _generate_recommendations(self, esa_score: float, green_score: float, 
                                  tree_score: float, esa_distance: float,
                                  green_distance: float, esa_features: List, 
                                  green_features: List) -> List[str]:
        """Generate specific recommendations based on scores."""
        recommendations = []
        
        # ESA Recommendations
        if esa_score < 5:
            if esa_distance > 1.5:
                recommendations.append(
                    f"🌿 Environmentally Significant Area Protection: "
                    f"Your location is {esa_distance:.2f}km from the nearest ESA. "
                    f"Consider ecological restoration efforts to connect to "
                    f"{esa_features[0]['feature']['ESA_NAME'] if esa_features else 'protected areas'}."
                )
            else:
                recommendations.append(
                    f"🌿 ESA Adjacency Opportunity: "
                    f"Project is near {esa_features[0]['feature']['ESA_NAME'] if esa_features else 'an ESA'}. "
                    f"Align development with ESA conservation goals to strengthen ecological corridors."
                )
        
        # Green Space Recommendations
        if green_score < 5:
            if green_distance > 0.4:
                recommendations.append(
                    f"🌳 Green Space Access Gap: "
                    f"Residents are {green_distance:.2f}km (target: 0.3km) from quality green space. "
                    f"Prioritize accessible park creation, community gardens, or urban reforestation."
                )
            else:
                recommendations.append(
                    f"🌳 Green Space Activation: "
                    f"Improve the quality and accessibility of the nearest green space at {green_distance:.2f}km. "
                    f"Enhanced trails, seating, and native plantings can maximize benefits."
                )
        elif green_distance <= 0.3:
            recommendations.append(
                f"✅ Strong Green Space Access: "
                f"Excellent proximity to {green_features[0]['feature'].get('AREA_NAME', 'green space')}. "
                f"Focus on enhancing quality and programming within this space."
            )
        
        # Tree Canopy Recommendations
        if tree_score < 7:
            recommendations.append(
                f"🌲 Street Tree Canopy Enhancement: "
                f"Current tree coverage is below the 30% canopy cover target. "
                f"Implement street tree planting initiatives and protect existing trees. "
                f"Prioritize native species for resilience."
            )
        
        # Holistic Recommendations
        if esa_score + green_score + tree_score < 15:
            recommendations.append(
                f"🌍 Comprehensive Ecological Enhancement: "
                f"This location would benefit from an integrated green infrastructure strategy "
                f"combining ESA protection, green space development, and urban forest expansion."
            )
        
        return recommendations
    
    def analyze_project_location(self, latitude: float, longitude: float, 
                                project_name: Optional[str] = None) -> Dict:
        """
        Comprehensive analysis of a project location.
        
        Args:
            latitude: Project latitude
            longitude: Project longitude
            project_name: Optional project name
            
        Returns:
            Complete analysis with scores, recommendations, and context
        """
        
        analysis = {
            'project_name': project_name or 'Unnamed Project',
            'coordinates': {'latitude': latitude, 'longitude': longitude},
            'ecological_sensitivity': self.calculate_ecological_sensitivity_score(latitude, longitude),
        }
        
        # Find nearby features
        analysis['nearby_features'] = {
            'environmentally_significant_areas': [
                {
                    'name': f['feature'].get('ESA_NAME', 'Unknown'),
                    'distance_km': f['distance_km']
                }
                for f in self.find_nearest_features(latitude, longitude, self.esa_data, 'LATITUDE', 'LONGITUDE', 1.5)[:3]
            ],
            'green_spaces': [
                {
                    'name': f['feature'].get('AREA_NAME', 'Unknown'),
                    'type': f['feature'].get('AREA_CLASS', 'Park'),
                    'distance_km': f['distance_km']
                }
                for f in self.find_nearest_features(latitude, longitude, self.green_spaces_data, 'LATITUDE', 'LONGITUDE', 1.0)[:3]
            ]
        }
        
        return analysis
    
    def generate_sustainability_prompt_enhancement(self, latitude: float, longitude: float) -> str:
        """
        Generate text to enhance the sustainability agent prompt with location-specific metrics.
        
        Args:
            latitude: Project latitude
            longitude: Project longitude
            
        Returns:
            Formatted string to add to agent system prompt
        """
        
        analysis = self.calculate_ecological_sensitivity_score(latitude, longitude)
        
        prompt_text = f"""
## Location-Based Ecological Metrics (Score: {analysis['total_score']}/30)

Ecological Sensitivity Analysis:
- ESA Proximity Score: {analysis['esa_score']}/10 (Nearest ESA: {analysis['nearest_esa'] or 'Not found'} at {analysis['esa_distance_km']}km)
- Green Space Proximity Score: {analysis['green_space_score']}/10 (Nearest park/green: {analysis['nearest_green_space'] or 'Not found'} at {analysis['green_distance_km']}km)
- Urban Canopy Score: {analysis['tree_score']}/10

Key Sustainability Metrics for This Location:
1. Green Space Target: All residents should be within 300m of a high-quality park (Current: {analysis['green_distance_km']}km)
2. Canopy Cover Target: Achieve 30% canopy coverage in surrounding area
3. Tree Coverage: Ensure at least 3 trees of decent size visible from residential areas
4. ESA Protection: {f"Located {analysis['esa_distance_km']}km from {analysis['nearest_esa']}" if analysis['nearest_esa'] else "No nearby ESA"}

Improvement Opportunities:
{chr(10).join([f"- {rec}" for rec in analysis['recommendations']])}
"""
        
        return prompt_text


# Initialize global analyzer
_analyzer = None

def get_analyzer() -> GeospatialMetricsAnalyzer:
    """Get or create the geospatial metrics analyzer."""
    global _analyzer
    if _analyzer is None:
        _analyzer = GeospatialMetricsAnalyzer()
    return _analyzer
