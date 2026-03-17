// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title AlertSystem
 * @dev Smart contract for automated alert generation based on threshold violations
 */
contract AlertSystem {
    
    enum AlertType { IMPURITY, OVERPRESSURE, LEAKAGE, CORROSION }
    enum AlertLevel { INFO, WARNING, CRITICAL }
    enum AlertStatus { ACTIVE, ACKNOWLEDGED, RESOLVED }
    
    struct Alert {
        uint256 alertId;
        uint256 timestamp;
        AlertType alertType;
        AlertLevel alertLevel;
        AlertStatus status;
        string sensorId;
        string description;
        uint256 value;           // The measured value that triggered alert
        uint256 threshold;       // The threshold that was exceeded
        address triggeredBy;
        address acknowledgedBy;
        uint256 acknowledgedTime;
        uint256 resolvedTime;
    }
    
    struct Threshold {
        uint256 warningLevel;
        uint256 criticalLevel;
        bool isActive;
    }
    
    // Storage
    Alert[] public alerts;
    mapping(AlertType => Threshold) public thresholds;
    mapping(address => bool) public authorizedOperators;
    address public admin;
    
    // Alert counters
    uint256 public activeAlertCount;
    uint256 public criticalAlertCount;
    
    // Events
    event AlertTriggered(
        uint256 indexed alertId,
        AlertType alertType,
        AlertLevel alertLevel,
        string sensorId,
        uint256 value,
        uint256 threshold
    );
    
    event AlertAcknowledged(
        uint256 indexed alertId,
        address acknowledgedBy,
        uint256 timestamp
    );
    
    event AlertResolved(
        uint256 indexed alertId,
        uint256 timestamp
    );
    
    event ThresholdUpdated(
        AlertType alertType,
        uint256 warningLevel,
        uint256 criticalLevel
    );
    
    // Modifiers
    modifier onlyAdmin() {
        require(msg.sender == admin, "Only admin");
        _;
    }
    
    modifier onlyAuthorizedOperator() {
        require(authorizedOperators[msg.sender] || msg.sender == admin, "Not authorized");
        _;
    }
    
    modifier alertExists(uint256 _alertId) {
        require(_alertId < alerts.length, "Alert does not exist");
        _;
    }
    
    constructor() {
        admin = msg.sender;
        authorizedOperators[msg.sender] = true;
        
        // Initialize default thresholds (values * 100 for precision)
        thresholds[AlertType.IMPURITY] = Threshold(10000, 15000, true);      // 100 ppm warning, 150 ppm critical
        thresholds[AlertType.OVERPRESSURE] = Threshold(9000, 10000, true);   // 90 bar warning, 100 bar critical
        thresholds[AlertType.LEAKAGE] = Threshold(1500, 2500, true);         // 15 ppm O2 warning, 25 ppm critical
        thresholds[AlertType.CORROSION] = Threshold(10000, 15000, true);     // Composite score
    }
    
    /**
     * @dev Add authorized operator
     */
    function addAuthorizedOperator(address _operator) public onlyAdmin {
        authorizedOperators[_operator] = true;
    }
    
    /**
     * @dev Update threshold for alert type
     */
    function updateThreshold(
        AlertType _alertType,
        uint256 _warningLevel,
        uint256 _criticalLevel
    ) public onlyAdmin {
        require(_warningLevel < _criticalLevel, "Warning must be less than critical");
        
        thresholds[_alertType] = Threshold(_warningLevel, _criticalLevel, true);
        
        emit ThresholdUpdated(_alertType, _warningLevel, _criticalLevel);
    }
    
    /**
     * @dev Trigger a new alert
     */
    function triggerAlert(
        AlertType _alertType,
        string memory _sensorId,
        string memory _description,
        uint256 _value
    ) public onlyAuthorizedOperator returns (uint256) {
        
        Threshold memory threshold = thresholds[_alertType];
        require(threshold.isActive, "Alert type not active");
        
        // Determine alert level
        AlertLevel level;
        uint256 thresholdValue;
        
        if (_value >= threshold.criticalLevel) {
            level = AlertLevel.CRITICAL;
            thresholdValue = threshold.criticalLevel;
            criticalAlertCount++;
        } else if (_value >= threshold.warningLevel) {
            level = AlertLevel.WARNING;
            thresholdValue = threshold.warningLevel;
        } else {
            level = AlertLevel.INFO;
            thresholdValue = threshold.warningLevel;
        }
        
        uint256 alertId = alerts.length;
        
        Alert memory newAlert = Alert({
            alertId: alertId,
            timestamp: block.timestamp,
            alertType: _alertType,
            alertLevel: level,
            status: AlertStatus.ACTIVE,
            sensorId: _sensorId,
            description: _description,
            value: _value,
            threshold: thresholdValue,
            triggeredBy: msg.sender,
            acknowledgedBy: address(0),
            acknowledgedTime: 0,
            resolvedTime: 0
        });
        
        alerts.push(newAlert);
        activeAlertCount++;
        
        emit AlertTriggered(alertId, _alertType, level, _sensorId, _value, thresholdValue);
        
        return alertId;
    }
    
    /**
     * @dev Acknowledge an alert
     */
    function acknowledgeAlert(uint256 _alertId) public onlyAuthorizedOperator alertExists(_alertId) {
        require(alerts[_alertId].status == AlertStatus.ACTIVE, "Alert not active");
        
        alerts[_alertId].status = AlertStatus.ACKNOWLEDGED;
        alerts[_alertId].acknowledgedBy = msg.sender;
        alerts[_alertId].acknowledgedTime = block.timestamp;
        
        emit AlertAcknowledged(_alertId, msg.sender, block.timestamp);
    }
    
    /**
     * @dev Resolve an alert
     */
    function resolveAlert(uint256 _alertId) public onlyAuthorizedOperator alertExists(_alertId) {
        require(
            alerts[_alertId].status == AlertStatus.ACTIVE || 
            alerts[_alertId].status == AlertStatus.ACKNOWLEDGED,
            "Alert already resolved"
        );
        
        if (alerts[_alertId].alertLevel == AlertLevel.CRITICAL) {
            criticalAlertCount--;
        }
        
        alerts[_alertId].status = AlertStatus.RESOLVED;
        alerts[_alertId].resolvedTime = block.timestamp;
        activeAlertCount--;
        
        emit AlertResolved(_alertId, block.timestamp);
    }
    
    /**
     * @dev Get alert details
     */
    function getAlert(uint256 _alertId) public view alertExists(_alertId) returns (
        uint256 timestamp,
        AlertType alertType,
        AlertLevel alertLevel,
        AlertStatus status,
        string memory sensorId,
        string memory description,
        uint256 value,
        uint256 threshold
    ) {
        Alert memory alert = alerts[_alertId];
        
        return (
            alert.timestamp,
            alert.alertType,
            alert.alertLevel,
            alert.status,
            alert.sensorId,
            alert.description,
            alert.value,
            alert.threshold
        );
    }
    
    /**
     * @dev Get total alert count
     */
    function getAlertCount() public view returns (uint256) {
        return alerts.length;
    }
    
    /**
     * @dev Get active alerts
     */
    function getActiveAlerts() public view returns (uint256[] memory) {
        uint256[] memory result = new uint256[](activeAlertCount);
        uint256 index = 0;
        
        for (uint256 i = 0; i < alerts.length; i++) {
            if (alerts[i].status == AlertStatus.ACTIVE) {
                result[index] = i;
                index++;
            }
        }
        
        return result;
    }
    
    /**
     * @dev Get critical alerts
     */
    function getCriticalAlerts() public view returns (uint256[] memory) {
        uint256[] memory result = new uint256[](criticalAlertCount);
        uint256 index = 0;
        
        for (uint256 i = 0; i < alerts.length; i++) {
            if (alerts[i].alertLevel == AlertLevel.CRITICAL && alerts[i].status != AlertStatus.RESOLVED) {
                result[index] = i;
                index++;
            }
        }
        
        return result;
    }
}
