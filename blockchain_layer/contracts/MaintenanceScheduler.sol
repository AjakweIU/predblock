// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title MaintenanceScheduler
 * @dev Smart contract for automated maintenance scheduling based on AI predictions
 */
contract MaintenanceScheduler {
    
    enum MaintenanceType { PREVENTIVE, CORRECTIVE, PREDICTIVE, EMERGENCY }
    enum MaintenanceStatus { SCHEDULED, IN_PROGRESS, COMPLETED, CANCELLED }
    enum Priority { LOW, MEDIUM, HIGH, URGENT }
    
    struct MaintenanceTask {
        uint256 taskId;
        uint256 scheduledTime;
        uint256 startTime;
        uint256 completionTime;
        MaintenanceType maintenanceType;
        MaintenanceStatus status;
        Priority priority;
        string location;
        string description;
        string[] requiredActions;
        address scheduledBy;
        address assignedTo;
        uint256 estimatedDuration;  // in seconds
        uint256 actualDuration;
        string completionNotes;
        bytes32 aiPredictionHash;   // Hash of AI prediction that triggered this
    }
    
    // Storage
    MaintenanceTask[] public tasks;
    mapping(address => bool) public authorizedSchedulers;
    mapping(address => bool) public maintenancePersonnel;
    mapping(address => uint256[]) public assignedTasks;
    address public admin;
    
    uint256 public pendingTaskCount;
    uint256 public urgentTaskCount;
    
    // Events
    event TaskScheduled(
        uint256 indexed taskId,
        uint256 scheduledTime,
        MaintenanceType maintenanceType,
        Priority priority,
        string location
    );
    
    event TaskAssigned(
        uint256 indexed taskId,
        address assignedTo,
        uint256 timestamp
    );
    
    event TaskStarted(
        uint256 indexed taskId,
        address startedBy,
        uint256 timestamp
    );
    
    event TaskCompleted(
        uint256 indexed taskId,
        uint256 completionTime,
        uint256 actualDuration
    );
    
    event TaskCancelled(
        uint256 indexed taskId,
        uint256 timestamp,
        address cancelledBy
    );
    
    // Modifiers
    modifier onlyAdmin() {
        require(msg.sender == admin, "Only admin");
        _;
    }
    
    modifier onlyAuthorizedScheduler() {
        require(authorizedSchedulers[msg.sender] || msg.sender == admin, "Not authorized to schedule");
        _;
    }
    
    modifier onlyMaintenancePersonnel() {
        require(maintenancePersonnel[msg.sender] || msg.sender == admin, "Not maintenance personnel");
        _;
    }
    
    modifier taskExists(uint256 _taskId) {
        require(_taskId < tasks.length, "Task does not exist");
        _;
    }
    
    constructor() {
        admin = msg.sender;
        authorizedSchedulers[msg.sender] = true;
        maintenancePersonnel[msg.sender] = true;
    }
    
    /**
     * @dev Add authorized scheduler (e.g., AI system address)
     */
    function addAuthorizedScheduler(address _scheduler) public onlyAdmin {
        authorizedSchedulers[_scheduler] = true;
    }
    
    /**
     * @dev Add maintenance personnel
     */
    function addMaintenancePersonnel(address _personnel) public onlyAdmin {
        maintenancePersonnel[_personnel] = true;
    }
    
    /**
     * @dev Schedule a new maintenance task
     */
    function scheduleTask(
        uint256 _scheduledTime,
        MaintenanceType _maintenanceType,
        Priority _priority,
        string memory _location,
        string memory _description,
        string[] memory _requiredActions,
        uint256 _estimatedDuration,
        bytes32 _aiPredictionHash
    ) public onlyAuthorizedScheduler returns (uint256) {
        
        require(_scheduledTime > block.timestamp, "Scheduled time must be in future");
        
        uint256 taskId = tasks.length;
        
        MaintenanceTask memory newTask = MaintenanceTask({
            taskId: taskId,
            scheduledTime: _scheduledTime,
            startTime: 0,
            completionTime: 0,
            maintenanceType: _maintenanceType,
            status: MaintenanceStatus.SCHEDULED,
            priority: _priority,
            location: _location,
            description: _description,
            requiredActions: _requiredActions,
            scheduledBy: msg.sender,
            assignedTo: address(0),
            estimatedDuration: _estimatedDuration,
            actualDuration: 0,
            completionNotes: "",
            aiPredictionHash: _aiPredictionHash
        });
        
        tasks.push(newTask);
        pendingTaskCount++;
        
        if (_priority == Priority.URGENT) {
            urgentTaskCount++;
        }
        
        emit TaskScheduled(taskId, _scheduledTime, _maintenanceType, _priority, _location);
        
        return taskId;
    }
    
    /**
     * @dev Assign task to maintenance personnel
     */
    function assignTask(uint256 _taskId, address _personnel) 
        public 
        onlyAuthorizedScheduler 
        taskExists(_taskId) 
    {
        require(maintenancePersonnel[_personnel], "Not authorized personnel");
        require(tasks[_taskId].status == MaintenanceStatus.SCHEDULED, "Task not in scheduled status");
        
        tasks[_taskId].assignedTo = _personnel;
        assignedTasks[_personnel].push(_taskId);
        
        emit TaskAssigned(_taskId, _personnel, block.timestamp);
    }
    
    /**
     * @dev Start a maintenance task
     */
    function startTask(uint256 _taskId) 
        public 
        onlyMaintenancePersonnel 
        taskExists(_taskId) 
    {
        require(
            tasks[_taskId].assignedTo == msg.sender || msg.sender == admin,
            "Task not assigned to you"
        );
        require(tasks[_taskId].status == MaintenanceStatus.SCHEDULED, "Task not scheduled");
        
        tasks[_taskId].status = MaintenanceStatus.IN_PROGRESS;
        tasks[_taskId].startTime = block.timestamp;
        
        emit TaskStarted(_taskId, msg.sender, block.timestamp);
    }
    
    /**
     * @dev Complete a maintenance task
     */
    function completeTask(uint256 _taskId, string memory _completionNotes) 
        public 
        onlyMaintenancePersonnel 
        taskExists(_taskId) 
    {
        require(
            tasks[_taskId].assignedTo == msg.sender || msg.sender == admin,
            "Task not assigned to you"
        );
        require(tasks[_taskId].status == MaintenanceStatus.IN_PROGRESS, "Task not in progress");
        
        tasks[_taskId].status = MaintenanceStatus.COMPLETED;
        tasks[_taskId].completionTime = block.timestamp;
        tasks[_taskId].actualDuration = block.timestamp - tasks[_taskId].startTime;
        tasks[_taskId].completionNotes = _completionNotes;
        
        pendingTaskCount--;
        
        if (tasks[_taskId].priority == Priority.URGENT) {
            urgentTaskCount--;
        }
        
        emit TaskCompleted(_taskId, block.timestamp, tasks[_taskId].actualDuration);
    }
    
    /**
     * @dev Cancel a maintenance task
     */
    function cancelTask(uint256 _taskId) 
        public 
        onlyAuthorizedScheduler 
        taskExists(_taskId) 
    {
        require(
            tasks[_taskId].status == MaintenanceStatus.SCHEDULED ||
            tasks[_taskId].status == MaintenanceStatus.IN_PROGRESS,
            "Task cannot be cancelled"
        );
        
        tasks[_taskId].status = MaintenanceStatus.CANCELLED;
        pendingTaskCount--;
        
        if (tasks[_taskId].priority == Priority.URGENT) {
            urgentTaskCount--;
        }
        
        emit TaskCancelled(_taskId, block.timestamp, msg.sender);
    }
    
    /**
     * @dev Get task details
     */
    function getTask(uint256 _taskId) public view taskExists(_taskId) returns (
        uint256 scheduledTime,
        MaintenanceType maintenanceType,
        MaintenanceStatus status,
        Priority priority,
        string memory location,
        string memory description,
        address assignedTo,
        uint256 estimatedDuration
    ) {
        MaintenanceTask memory task = tasks[_taskId];
        
        return (
            task.scheduledTime,
            task.maintenanceType,
            task.status,
            task.priority,
            task.location,
            task.description,
            task.assignedTo,
            task.estimatedDuration
        );
    }
    
    /**
     * @dev Get total task count
     */
    function getTaskCount() public view returns (uint256) {
        return tasks.length;
    }
    
    /**
     * @dev Get tasks assigned to personnel
     */
    function getAssignedTasks(address _personnel) public view returns (uint256[] memory) {
        return assignedTasks[_personnel];
    }
    
    /**
     * @dev Get pending tasks
     */
    function getPendingTasks() public view returns (uint256[] memory) {
        uint256[] memory result = new uint256[](pendingTaskCount);
        uint256 index = 0;
        
        for (uint256 i = 0; i < tasks.length; i++) {
            if (tasks[i].status == MaintenanceStatus.SCHEDULED || 
                tasks[i].status == MaintenanceStatus.IN_PROGRESS) {
                result[index] = i;
                index++;
            }
        }
        
        return result;
    }
    
    /**
     * @dev Get urgent tasks
     */
    function getUrgentTasks() public view returns (uint256[] memory) {
        uint256[] memory result = new uint256[](urgentTaskCount);
        uint256 index = 0;
        
        for (uint256 i = 0; i < tasks.length; i++) {
            if (tasks[i].priority == Priority.URGENT && 
                tasks[i].status != MaintenanceStatus.COMPLETED &&
                tasks[i].status != MaintenanceStatus.CANCELLED) {
                result[index] = i;
                index++;
            }
        }
        
        return result;
    }
    
    /**
     * @dev Get overdue tasks
     */
    function getOverdueTasks() public view returns (uint256[] memory) {
        uint256 count = 0;
        
        // Count overdue tasks
        for (uint256 i = 0; i < tasks.length; i++) {
            if (tasks[i].scheduledTime < block.timestamp && 
                (tasks[i].status == MaintenanceStatus.SCHEDULED ||
                 tasks[i].status == MaintenanceStatus.IN_PROGRESS)) {
                count++;
            }
        }
        
        uint256[] memory result = new uint256[](count);
        uint256 index = 0;
        
        for (uint256 i = 0; i < tasks.length; i++) {
            if (tasks[i].scheduledTime < block.timestamp && 
                (tasks[i].status == MaintenanceStatus.SCHEDULED ||
                 tasks[i].status == MaintenanceStatus.IN_PROGRESS)) {
                result[index] = i;
                index++;
            }
        }
        
        return result;
    }
}
