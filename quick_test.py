# -*- coding: utf-8 -*-
"""Quick test for comprehensive evaluation metrics"""

from comprehensive_evaluation_metrics import integrate_comprehensive_metrics

def quick_test():
    """Quick test of the evaluation system"""
    
    # Simple test document
    test_doc = """
    Pressure Instrument Installation Specification
    
    Installation Requirements:
    - Height: 1.2-1.5m from ground for easy observation
    - Straight pipe: 10D upstream, 5D downstream
    - Environment: -40°C to +85°C, humidity ≤85%
    
    Installation Steps:
    1. First prepare tools: wrench, screwdriver, measurement tools
    2. Then fix with bolts using wrench, torque 15-20N·m
    3. Finally calibrate and verify accuracy and response time
    
    Materials:
    - Pressure transmitter: DN50, PN16, accuracy ±0.5%, 304 stainless steel
    - Bolts: M16×50, quantity 8 sets, 304 stainless steel
    - Gasket: PTFE gasket, temperature resistant -200°C to +250°C
    
    Safety Measures:
    - Personnel protection: safety helmet, protective glasses, insulated gloves
    - Risk control: identify high pressure, corrosion, poisoning risks, emergency plan
    - Safety interlock: set pressure alarm and safety interlock protection
    
    Quality Control:
    - Acceptance standard: according to GB/T 18271-2017
    - Check points: sealing, accuracy, response time, alarm function
    - Maintenance: monthly check, quarterly calibration
    - Fault handling: common faults include zero drift, range drift
    """
    
    print("Testing Comprehensive Evaluation Metrics System")
    print("=" * 50)
    
    try:
        # Run comprehensive evaluation
        result = integrate_comprehensive_metrics(test_doc)
        
        # Extract key metrics
        comprehensive_score = result['comprehensive_score']
        comprehensive_level = result['comprehensive_level']
        coverage_score = result['content_coverage']['overall_coverage_score']
        usability_score = result['usability_operability']['usability_score']
        quality_score = result['quality_review']['aggregated'].get('overall_quality_score', 0)
        
        # Display results
        print(f"\nComprehensive Score: {comprehensive_score:.1f}/100 ({comprehensive_level})")
        print(f"Content Coverage: {coverage_score:.1f}/100")
        print(f"Usability: {usability_score:.1f}/100")
        print(f"Quality Review: {quality_score:.1f}/100")
        
        # Show feedback
        feedback = result['content_coverage']['feedback_for_llm']
        print(f"Improvement Suggestions: {feedback}")
        
        # Show advanced checks
        advanced_checks = result['usability_operability']['advanced_checks']
        print(f"\nAdvanced Checks:")
        print(f"  - Sequence Consistency: {advanced_checks['sequence_consistency']}/10")
        print(f"  - Tool-Step Alignment: {advanced_checks['tool_step_alignment']}/15")
        print(f"  - Dimension Reasonableness: {advanced_checks['dimension_reasonableness']}/10")
        
        print(f"\nTest Successful! Evaluation system is working properly.")
        
        return result
        
    except Exception as e:
        print(f"Test Failed: {str(e)}")
        return None

if __name__ == "__main__":
    quick_test() 
 
 