// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title MonitoringLog
 * @dev Immutable storage of CCS pipeline monitoring data
 */
contract MonitoringLog {
    
    struct MonitoringRecord {
        uint256 timestamp;
        uint256 pressure;        // in bar * 100 (to handle decimals)
        uint256 temperature;     // in Celsius * 100
        uint256 flowRate;        // in kg/s * 100
        uint256 h2oLevel;        // in ppmv
        uint256 h2sLevel;        // in ppmv
        uint256 so2Level;        // in ppmv
        uint256 o2Level;         // in ppmv
        uint256 noxLevel;        // in ppmv
        string sensorId;
        address recorder;
        bytes32 dataHash;        // Hash of complete data for verification
    }
    
    // Storage
    MonitoringRecord[] public records;
    mapping(bytes32 => bool) public recordExists;
    
    // Events
    event RecordAdded(
        uint256 indexed recordId,
        uint256 timestamp,
        string sensorId,
        address recorder,
        bytes32 dataHash
    );
    
    // Modifiers
    modifier validData(uint256 _pressure, uint256 _temperature) {
        require(_pressure > 0 && _pressure < 15000, "Invalid pressure");
        require(_temperature > 0 && _temperature < 10000, "Invalid temperature");
        _;
    }
    
    /**
     * @dev Add a new monitoring record
     */
    function addRecord(
        uint256 _pressure,
        uint256 _temperature,
        uint256 _flowRate,
        uint256 _h2oLevel,
        uint256 _h2sLevel,
        uint256 _so2Level,
        uint256 _o2Level,
        uint256 _noxLevel,
        string memory _sensorId
    ) public validData(_pressure, _temperature) returns (uint256) {
        
        // Create data hash for integrity verification
        bytes32 dataHash = keccak256(abi.encodePacked(
            block.timestamp,
            _pressure,
            _temperature,
            _flowRate,
            _h2oLevel,
            _h2sLevel,
            _so2Level,
            _o2Level,
            _noxLevel,
            _sensorId,
            msg.sender
        ));
        
        require(!recordExists[dataHash], "Record already exists");
        
        MonitoringRecord memory newRecord = MonitoringRecord({
            timestamp: block.timestamp,
            pressure: _pressure,
            temperature: _temperature,
            flowRate: _flowRate,
            h2oLevel: _h2oLevel,
            h2sLevel: _h2sLevel,
            so2Level: _so2Level,
            o2Level: _o2Level,
            noxLevel: _noxLevel,
            sensorId: _sensorId,
            recorder: msg.sender,
            dataHash: dataHash
        });
        
        records.push(newRecord);
        recordExists[dataHash] = true;
        
        uint256 recordId = records.length - 1;
        
        emit RecordAdded(recordId, block.timestamp, _sensorId, msg.sender, dataHash);
        
        return recordId;
    }
    
    /**
     * @dev Get a specific record by ID
     */
    function getRecord(uint256 _recordId) public view returns (
        uint256 timestamp,
        uint256 pressure,
        uint256 temperature,
        uint256 flowRate,
        uint256 h2oLevel,
        uint256 h2sLevel,
        uint256 so2Level,
        uint256 o2Level,
        uint256 noxLevel,
        string memory sensorId,
        address recorder,
        bytes32 dataHash
    ) {
        require(_recordId < records.length, "Record does not exist");
        
        MonitoringRecord memory record = records[_recordId];
        
        return (
            record.timestamp,
            record.pressure,
            record.temperature,
            record.flowRate,
            record.h2oLevel,
            record.h2sLevel,
            record.so2Level,
            record.o2Level,
            record.noxLevel,
            record.sensorId,
            record.recorder,
            record.dataHash
        );
    }
    
    /**
     * @dev Get total number of records
     */
    function getRecordCount() public view returns (uint256) {
        return records.length;
    }
    
    /**
     * @dev Verify record integrity
     */
    function verifyRecord(uint256 _recordId) public view returns (bool) {
        require(_recordId < records.length, "Record does not exist");
        
        MonitoringRecord memory record = records[_recordId];
        
        bytes32 computedHash = keccak256(abi.encodePacked(
            record.timestamp,
            record.pressure,
            record.temperature,
            record.flowRate,
            record.h2oLevel,
            record.h2sLevel,
            record.so2Level,
            record.o2Level,
            record.noxLevel,
            record.sensorId,
            record.recorder
        ));
        
        return computedHash == record.dataHash;
    }
}
