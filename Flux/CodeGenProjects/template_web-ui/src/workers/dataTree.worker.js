import { cloneDeep, get } from 'lodash';
import { generateTreeStructure } from '../utils/core/treeUtils';
// Assuming DATA_TYPES and ITEMS_PER_PAGE are available globally or passed if not using a module loader that handles this.
// For robustness, they can be passed in the message payload or explicitly imported if your setup supports it.
// Fallback to constants imported here if not provided in payload.
import { DATA_TYPES as DATA_TYPES_CONSTANT, ITEMS_PER_PAGE as ITEMS_PER_PAGE_CONSTANT } from '../constants';

/**
 * Processes a node from the generated tree structure (from generateTreeStructure)
 * and flattens it for the TreeView component, handling pagination.
 * This is an adaptation of the processNode logic from DataTree.jsx.
 */
function workerProcessNode(node, parentId, paginatedNodes, ITEMS_PER_PAGE, allFlattenedNodes, enableObjectPagination) {
    // Use xpath as ID, ensure it's a string and handle null/undefined
    // Nodes from generateTreeStructure should have an xpath.
    const currentId = node.xpath || String(Math.random());

    const treeNode = {
        name: node.name || node.key || "", // Ensure name is a string
        children: [],
        id: currentId,
        parent: parentId,
        metadata: node // This 'node' is the one from generateTreeStructure output
    };

    allFlattenedNodes.push(treeNode);

    const metadataFromGenTree = node; // This is the node object from generateTreeStructure

    let applyPagination = false;
    if (metadataFromGenTree.isArrayContainer) {
        applyPagination = true; // Always apply for array containers
    } else if (metadataFromGenTree.isObjectContainer && enableObjectPagination) {
        applyPagination = true; // Apply for object containers if prop is true
    }

    if (applyPagination && metadataFromGenTree.children && metadataFromGenTree.children.length > ITEMS_PER_PAGE) {
        const nodePaginationState = paginatedNodes[currentId] || { page: 0 };
        const totalPages = Math.ceil(metadataFromGenTree.children.length / ITEMS_PER_PAGE);
        // Ensure page is within bounds
        const currentPage = Math.max(0, Math.min(nodePaginationState.page, totalPages - 1));

        if (treeNode.metadata) { // treeNode.metadata is the same as metadataFromGenTree here
            treeNode.metadata.pagination = {
                currentPage: currentPage,
                totalPages: totalPages,
                totalItems: metadataFromGenTree.children.length,
                // onPageChange is not set here; main thread handles interactions
            };
        }

        const startIndex = currentPage * ITEMS_PER_PAGE;
        const endIndex = Math.min(startIndex + ITEMS_PER_PAGE, metadataFromGenTree.children.length);
        const visibleChildren = metadataFromGenTree.children.slice(startIndex, endIndex);

        visibleChildren.forEach(childNode => {
            // Pass enableObjectPagination down recursively
            const childId = workerProcessNode(childNode, currentId, paginatedNodes, ITEMS_PER_PAGE, allFlattenedNodes, enableObjectPagination);
            if (childId) { // Ensure childId is valid before pushing
                treeNode.children.push(childId);
            }
        });

    } else if (metadataFromGenTree.children && metadataFromGenTree.children.length > 0) {
        metadataFromGenTree.children.forEach(childNode => {
            // Pass enableObjectPagination down recursively
            const childId = workerProcessNode(childNode, currentId, paginatedNodes, ITEMS_PER_PAGE, allFlattenedNodes, enableObjectPagination);
            if (childId) { // Ensure childId is valid before pushing
                treeNode.children.push(childId);
            }
        });
    }
    // It's crucial that 'node.xpath' exists and is unique for 'currentId' to be effective.
    // If node.xpath can be undefined or not unique for identifiable nodes, IDs might clash or be unstable.
    return currentId;
}


onmessage = (e) => {
    const {
        projectSchema, modelName, updatedData, storedData, subtree, mode, xpath,
        selectedId, showHidden, paginatedNodes, filters,
        quickFilter,
        enableObjectPagination,
        disablePagination
    } = e.data.payload;

    // Use constants from payload if provided, otherwise use imported ones.
    const ITEMS_PER_PAGE = e.data.payload.ITEMS_PER_PAGE || ITEMS_PER_PAGE_CONSTANT;
    const DATA_TYPES = e.data.payload.DATA_TYPES || DATA_TYPES_CONSTANT; // Not directly used in this snippet but good practice

    // Add a guard to prevent processing when data is empty
    if (!projectSchema || !modelName || !updatedData || !storedData || (Object.keys(updatedData).length === 0 && Object.keys(storedData).length === 0)) {
        // Just return, don't post a message, to avoid potential loops.
        // The main thread should manage loading state.
        postMessage({
            type: 'TREE_GENERATED',
            payload: {
                originalTree: [],
                treeData: [{
                    name: modelName || 'Root',
                    children: [],
                    id: "root",
                    parent: null,
                    metadata: { name: modelName || 'Root', isRoot: true }
                }]
            }
        });
        return;
    }

    // Handle subtree processing for optimized updates
    if (e.data.type === 'PROCESS_SUBTREE') {
        const subtreeData = e.data.payload.subtreeData;
        const flattenedNodes = [];

        if (subtreeData && typeof subtreeData === 'object') {
            const nodeId = workerProcessNode(subtreeData, "root", paginatedNodes, ITEMS_PER_PAGE, flattenedNodes, enableObjectPagination);
            postMessage({
                type: 'SUBTREE_GENERATED',
                payload: {
                    subtree: flattenedNodes,
                    nodeId: nodeId
                }
            });
        }
        return;
    }

    // CallerProps for generateTreeStructure.
    // IMPORTANT: Event handlers (onTextChange, etc.) are NOT included.
    // The 'isOpen' logic: generateTreeStructure uses an internal global 'treeState'.
    // This state will be local to the worker. The main thread's TreeView component will control actual expansion.
    const callerPropsForWorker = {
        'data': cloneDeep(updatedData), // Worker operates on its own copy
        'isOpen': true, // Affects root of generated tree if not in worker's treeState
        'hide': !showHidden,
        'showDataType': false,
        'originalData': cloneDeep(storedData),
        'subtree': subtree,
        'mode': mode,
        'xpath': xpath, // Root xpath for this tree generation context
        'index': selectedId,
        'forceUpdate': false,
        'filters': filters,
        'paginatedNodes': paginatedNodes, // Pass pagination state to tree generation
        'quickFilter': quickFilter ?? null,
        'disablePagination': disablePagination // <-- Pass to tree logic
    };

    const generatedTree = generateTreeStructure(cloneDeep(projectSchema), modelName, callerPropsForWorker);

    const flattenedNodes = [];
    const rootId = "root"; // Synthetic root for react-accessible-treeview

    flattenedNodes.push({
        name: modelName,
        children: [],
        id: rootId,
        parent: null,
        metadata: { name: modelName, isRoot: true } // Basic metadata for root
    });

    generatedTree.forEach(node => {
        // Ensure 'node' is a valid object before processing
        if (node && typeof node === 'object') {
            // Pass enableObjectPagination to workerProcessNode
            const nodeId = workerProcessNode(node, rootId, paginatedNodes, ITEMS_PER_PAGE, flattenedNodes, enableObjectPagination);
            // Ensure the root's children array exists before pushing
            if (flattenedNodes[0] && flattenedNodes[0].children && nodeId) {
                flattenedNodes[0].children.push(nodeId);
            }
        }
    });

    postMessage({
        type: 'TREE_GENERATED',
        payload: {
            originalTree: generatedTree,
            treeData: flattenedNodes
        }
    });
};
