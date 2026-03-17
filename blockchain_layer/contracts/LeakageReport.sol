// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title LeakageReport
 * @dev Tamper-proof leakage incident reporting system
 */
contract LeakageReport {
    
    enum Severity { LOW, MEDIUM, HIGH, CRITICAL }
    enum Status { REPORTED, INVESTIGATING, CONFIRMED, RESOLVED, FALSE_ALARM }
    
    struct LeakageIncident {
        uint256 incidentId;
        uint256 timestamp;
        uint256 detectionTimestamp;
        string location;
        Severity severity;
        Status status;
        uint256 pressureDrop;      // in bar * 100
        uint256 o2Level;           // in ppmv
        uint256 acousticSignal;    // arbitrary units
        string description;
        address reporter;
        address[] investigators;
        string resolutionNotes;
        uint256 resolvedTimestamp;
        bytes32 evidenceHash;
    }
    
    // Storage
    LeakageIncident[] public incidents;
    mapping(address => bool) public authorizedReporters;
    mapping(address => bool) public authorizedInvestigators;
    address public admin;
    
    // Events
    event IncidentReported(
        uint256 indexed incidentId,
        uint256 timestamp,
        string location,
        Severity severity,
        address reporter
    );
    
    event IncidentStatusUpdated(
        uint256 indexed incidentId,
        Status newStatus,
        address updatedBy
    );
    
    event IncidentResolved(
        uint256 indexed incidentId,
        uint256 resolvedTimestamp,
        string resolutionNotes
    );
    
    event InvestigatorAssigned(
        uint256 indexed incidentId,
        address investigator
    );
    
    // Modifiers
    modifier onlyAdmin() {
        require(msg.sender == admin, "Only admin can perform this action");
        _;
    }
    
    modifier onlyAuthorizedReporter() {
        require(authorizedReporters[msg.sender], "Not authorized to report");
        _;
    }
    
    modifier onlyAuthorizedInvestigator() {
        require(authorizedInvestigators[msg.sender], "Not authorized to investigate");
        _;
    }
    
    modifier incidentExists(uint256 _incidentId) {
        require(_incidentId < incidents.length, "Incident does not exist");
        _;
    }
    
    constructor() {
        admin = msg.sender;
        authorizedReporters[msg.sender] = true;
        authorizedInvestigators[msg.sender] = true;
    }
    
    /**
     * @dev Add authorized reporter
     */
    function addAuthorizedReporter(address _reporter) public onlyAdmin {
        authorizedReporters[_reporter] = true;
    }
    
    /**
     * @dev Add authorized investigator
     */
    function addAuthorizedInvestigator(address _investigator) public onlyAdmin {
        authorizedInvestigators[_investigator] = true;
    }
    
    /**
     * @dev Report a new leakage incident
     */
    function reportIncident(
        uint256 _detectionTimestamp,
        string memory _location,
        Severity _severity,
        uint256 _pressureDrop,
        uint256 _o2Level,
        uint256 _acousticSignal,
        string memory _description,
        bytes32 _evidenceHash
    ) public onlyAuthorizedReporter returns (uint256) {
        
        uint256 incidentId = incidents.length;
        
        LeakageIncident memory newIncident = LeakageIncident({
            incidentId: incidentId,
            timestamp: block.timestamp,
            detectionTimestamp: _detectionTimestamp,
            location: _location,
            severity: _severity,
            status: Status.REPORTED,
            pressureDrop: _pressureDrop,
            o2Level: _o2Level,
            acousticSignal: _acousticSignal,
            description: _description,
            reporter: msg.sender,
            investigators: new address[](0),
            resolutionNotes: "",
            resolvedTimestamp: 0,
            evidenceHash: _evidenceHash
        });
        
        incidents.push(newIncident);
        
        emit IncidentReported(incidentId, block.timestamp, _location, _severity, msg.sender);
        
        return incidentId;
    }
    
    /**
     * @dev Update incident status
     */
    function updateIncidentStatus(
        uint256 _incidentId,
        Status _newStatus
    ) public onlyAuthorizedInvestigator incidentExists(_incidentId) {
        
        incidents[_incidentId].status = _newStatus;
        
        emit IncidentStatusUpdated(_incidentId, _newStatus, msg.sender);
    }
    
    /**
     * @dev Assign investigator to incident
     */
    function assignInvestigator(
        uint256 _incidentId,
        address _investigator
    ) public onlyAdmin incidentExists(_incidentId) {
        
        require(authorizedInvestigators[_investigator], "Not an authorized investigator");
        
        incidents[_incidentId].investigators.push(_investigator);
        
        emit InvestigatorAssigned(_incidentId, _investigator);
    }
    
    /**
     * @dev Resolve incident
     */
    function resolveIncident(
        uint256 _incidentId,
        string memory _resolutionNotes
    ) public onlyAuthorizedInvestigator incidentExists(_incidentId) {
        
        incidents[_incidentId].status = Status.RESOLVED;
        incidents[_incidentId].resolutionNotes = _resolutionNotes;
        incidents[_incidentId].resolvedTimestamp = block.timestamp;
        
        emit IncidentResolved(_incidentId, block.timestamp, _resolutionNotes);
    }
    
    /**
     * @dev Get incident details
     */
    function getIncident(uint256 _incidentId) public view incidentExists(_incidentId) returns (
        uint256 timestamp,
        string memory location,
        Severity severity,
        Status status,
        uint256 pressureDrop,
        uint256 o2Level,
        string memory description,
        address reporter
    ) {
        LeakageIncident memory incident = incidents[_incidentId];
        
        return (
            incident.timestamp,
            incident.location,
            incident.severity,
            incident.status,
            incident.pressureDrop,
            incident.o2Level,
            incident.description,
            incident.reporter
        );
    }
    
    /**
     * @dev Get total number of incidents
     */
    function getIncidentCount() public view returns (uint256) {
        return incidents.length;
    }
    
    /**
     * @dev Get incidents by status
     */
    function getIncidentsByStatus(Status _status) public view returns (uint256[] memory) {
        uint256 count = 0;
        
        // Count matching incidents
        for (uint256 i = 0; i < incidents.length; i++) {
            if (incidents[i].status == _status) {
                count++;
            }
        }
        
        // Create result array
        uint256[] memory result = new uint256[](count);
        uint256 index = 0;
        
        for (uint256 i = 0; i < incidents.length; i++) {
            if (incidents[i].status == _status) {
                result[index] = i;
                index++;
            }
        }
        
        return result;
    }
}
