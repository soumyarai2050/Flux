import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { cloneDeep, get, set } from 'lodash';
import { ErrorBoundary } from 'react-error-boundary';
import PropTypes from 'prop-types';
import {
    Box,
    Typography,
    useTheme,
    IconButton,
    Dialog,
    DialogContent,
    Button,
    Tooltip,
    CircularProgress,
    Alert,
    TextField,
    InputAdornment
} from '@mui/material';
import {
    ChevronLeft,
    ChevronRight,
    Send
} from '@mui/icons-material';
import MarkdownRenderer from './MarkdownRenderer';
import ClipboardCopier from '../../utility/ClipboardCopier';
import ChatMessage from './ChatMessage';
import { DB_ID, MODES } from '../../../constants';
import { clearxpath, generateObjectFromSchema, getModelSchema } from '../../../utils';
import styles from './ChatView.module.css';

/**
 * ChatView displays conversation data in a chat-like format with inline editing.
 * Uses Redux directly for state management and data updates.
 * - Shows edit pencils only when mode === 'edit'
 * - Updates Redux state via actions.setUpdatedObj() when edits are saved
 * - Manages its own collapse state locally
 */
// Error fallback component
function ErrorFallback({ error, resetErrorBoundary }) {
    return (
        <Box className={styles.emptyState}>
            <Alert severity="error" sx={{ width: '100%', maxWidth: 400 }}>
                <Typography variant="h6" gutterBottom>
                    Something went wrong
                </Typography>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                    {error.message || 'An unexpected error occurred'}
                </Typography>
                <Button onClick={resetErrorBoundary} variant="outlined" size="small">
                    Try again
                </Button>
            </Alert>
        </Box>
    );
}

// Loading component
function LoadingState() {
    return (
        <Box className={styles.emptyState}>
            <CircularProgress size={40} />
            <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
                Loading conversation...
            </Typography>
        </Box>
    );
}

function ChatView({
    modelName,
    modelDataSource,
    onModeToggle,
    onSave
}) {
    const { schema: projectSchema } = useSelector(state => state.schema);
    const { actions, selector, fieldsMetadata } = modelDataSource;
    const { updatedObj, mode, loading, error } = useSelector(selector);
    const { contextId } = useSelector(state => state[modelName]);
    const dispatch = useDispatch();

    // Local UI state
    const [isCollapsed, setIsCollapsed] = useState(false);

    const [viewReasoningDialogOpen, setViewReasoningDialogOpen] = useState(false);
    const [viewReasoningDialogContent, setViewReasoningDialogContent] = useState('');

    const [viewMessageDialogOpen, setViewMessageDialogOpen] = useState(false);
    const [viewMessageDialogContent, setViewMessageDialogContent] = useState('');
    const [viewMessageDialogField, setViewMessageDialogField] = useState(null);
    const [modalEditText, setModalEditText] = useState('');

    const [editingField, setEditingField] = useState(null);
    const [editText, setEditText] = useState('');
    const [clipboardText, setClipboardText] = useState(null);
    const [inputMessage, setInputMessage] = useState('');

    const contextIdRef = useRef();
    contextIdRef.current = contextId;

    // Focus management refs
    const contextElementsRef = useRef(new Map());
    const messagesContainerRef = useRef(null);

    const theme = useTheme();
    const isDarkMode = theme.palette.mode === 'dark';

    const chatAttributes = useMemo(() => {
        const contextMeta = fieldsMetadata.find((o) => o.chat_context);
        const contextRefs = contextMeta.$ref?.split('/');
        const contextSchemaName = contextRefs[contextRefs.length - 1];
        const contextPath = contextMeta.tableTitle;
        const contextParentPath = contextMeta.parentxpath;
        const conversationMeta = fieldsMetadata.find((o) => o.chat_conversation);
        const hasNestedConversation = Boolean(conversationMeta);
        const conversationRelPath = hasNestedConversation ? conversationMeta.key : '';
        const userMessageMeta = fieldsMetadata.find((o) => o.user_message);
        const botMessageMeta = fieldsMetadata.find((o) => o.bot_message);
        const botReasoningMeta = fieldsMetadata.find((o) => o.bot_reasoning);
        const userMessageRelPath = [conversationRelPath, userMessageMeta.key].filter(Boolean).join('.');
        const botMessageRelPath = [conversationRelPath, botMessageMeta.key].filter(Boolean).join('.');
        const botReasoningRelPath = [conversationRelPath, botReasoningMeta.key].filter(Boolean).join('.');

        return {
            contextParentPath,
            contextSchemaName,
            contextPath,
            conversationRelPath,
            userMessageRelPath,
            botMessageRelPath,
            botReasoningRelPath
        }
    }, [])

    const chatContexts = useMemo(() => get(updatedObj, chatAttributes.contextPath) || [], [updatedObj]);
    const activeChatContext = useMemo(() => {
        if (contextId) {
            return chatContexts.find((o) => o[DB_ID] === contextId);
        }
        return null;
    }, [contextId, chatContexts])

    // Focus management utility
    const focusContext = useCallback((targetContextId) => {
        const element = contextElementsRef.current.get(targetContextId);
        if (element) {
            element.focus();
        }
    }, []);

    // Get next/previous context for navigation
    const getNavigationContext = useCallback((direction) => {
        if (!chatContexts.length) return null;

        const currentIndex = chatContexts.findIndex(ctx => ctx[DB_ID] === contextId);

        switch (direction) {
            case 'next':
                return currentIndex < chatContexts.length - 1
                    ? chatContexts[currentIndex + 1][DB_ID]
                    : chatContexts[0][DB_ID]; // Wrap to first
            case 'previous':
                return currentIndex > 0
                    ? chatContexts[currentIndex - 1][DB_ID]
                    : chatContexts[chatContexts.length - 1][DB_ID]; // Wrap to last
            case 'first':
                return chatContexts[0][DB_ID];
            case 'last':
                return chatContexts[chatContexts.length - 1][DB_ID];
            default:
                return null;
        }
    }, [chatContexts, contextId]);

    useEffect(() => {
        let targetContextId = contextIdRef.current;

        if (chatContexts.length === 0) {
            targetContextId = null;
        } else if (contextIdRef.current === null) {
            targetContextId = chatContexts[chatContexts.length - 1][DB_ID];
        } else {
            const exists = chatContexts.some((o) => o[DB_ID] === contextIdRef.current);
            if (!exists) {
                targetContextId = null;
            }
        }

        if (targetContextId !== contextIdRef.current) {
            dispatch(actions.setContextId(targetContextId));
        }
    }, [chatContexts, dispatch]);

    // Context selection handler
    const handleContextSelect = useCallback((updatedContextId) => {
        if (mode !== MODES.READ) return;

        if (contextIdRef.current !== updatedContextId) {
            dispatch(actions.setContextId(updatedContextId));
        }
    }, [mode, dispatch]);

    const handleCancelEdit = useCallback(() => {
        setEditingField(null);
        setEditText('');
        onModeToggle();
    }, [onModeToggle]);

    // Keyboard navigation handler
    const handleKeyDown = useCallback((event) => {
        if (mode !== MODES.READ) return;

        // Handle edit mode escape
        if (editingField && event.key === 'Escape') {
            event.preventDefault();
            handleCancelEdit();
            return;
        }

        // Don't handle navigation if in edit mode
        if (editingField) return;

        let targetContextId = null;
        let shouldPrevent = false;

        switch (event.key) {
            case 'Enter':
            case ' ':
                // These handle selection on the focused element
                shouldPrevent = true;
                break;
            case 'ArrowDown':
                targetContextId = getNavigationContext('next');
                shouldPrevent = true;
                break;
            case 'ArrowUp':
                targetContextId = getNavigationContext('previous');
                shouldPrevent = true;
                break;
            case 'Home':
                targetContextId = getNavigationContext('first');
                shouldPrevent = true;
                break;
            case 'End':
                targetContextId = getNavigationContext('last');
                shouldPrevent = true;
                break;
            case 'Escape':
                // Clear selection and focus
                if (contextId) {
                    dispatch(actions.setContextId(null));
                }
                shouldPrevent = true;
                break;
        }

        if (shouldPrevent) {
            event.preventDefault();
        }

        if (targetContextId && targetContextId !== contextId) {
            dispatch(actions.setContextId(targetContextId));
            // Focus immediately without waiting for state update
            focusContext(targetContextId);
        }
    }, [mode, editingField, handleCancelEdit, getNavigationContext, contextId, dispatch, actions]);

    // Dialog handlers
    const handleOpenReasoningDialog = useCallback((content) => {
        setViewReasoningDialogContent(content);
        setViewReasoningDialogOpen(true);
    }, []);

    const handleCloseReasoningDialog = useCallback(() => {
        setViewReasoningDialogOpen(false);
    }, []);

    const handleOpenViewMessageDialog = useCallback((content, field = null) => {
        setViewMessageDialogContent(content);
        setViewMessageDialogField(field);
        setModalEditText(content || '');
        setViewMessageDialogOpen(true);
    }, []);

    const handleCloseViewMessageDialog = useCallback(() => {
        setViewMessageDialogOpen(false);
        setViewMessageDialogField(null);
    }, []);

    const handleModalTextChange = useCallback((newText) => {
        setModalEditText(newText);
        // Update the main edit text if this is for the currently editing field
        if (viewMessageDialogField === editingField) {
            setEditText(newText);
        }
    }, [viewMessageDialogField, editingField]);

    const handleCopyMessage = useCallback((content) => {
        if (!content) return;
        setClipboardText(content);
        setTimeout(() => {
            setClipboardText(null);
        }, 1000);
    }, []);

    const handleStartEdit = useCallback((field) => {
        if (mode === MODES.READ) {
            onModeToggle();
        };
        setEditingField(field);
        const conversation = get(activeChatContext, chatAttributes.conversationRelPath || '');
        setEditText(conversation?.[field] || '');
    }, [mode, activeChatContext, onModeToggle]);

    const handleSaveEdit = useCallback(() => {
        if (editingField && activeChatContext) {
            const updatedData = cloneDeep(updatedObj);
            const udpatedContexts = get(updatedData, chatAttributes.contextPath);
            if (udpatedContexts && Array.isArray(udpatedContexts)) {
                const context = udpatedContexts.find((o) => o[DB_ID] === contextIdRef.current);
                if (context) {
                    const conversation = get(context, chatAttributes.conversationRelPath || '');
                    conversation[editingField] = editText;
                    dispatch(actions.setUpdatedObj(updatedData));
                    onSave(clearxpath(cloneDeep(updatedData)), undefined, undefined, true);
                }
            }
        }
        handleCancelEdit();
    }, [editingField, activeChatContext, updatedObj, editText, dispatch, actions, handleCancelEdit, onSave]);

    const handleSend = useCallback(() => {
        const updatedData = cloneDeep(updatedObj);
        const contextSchema = getModelSchema(chatAttributes.contextSchemaName, projectSchema);
        const newObj = generateObjectFromSchema(projectSchema, contextSchema, undefined, chatAttributes.contextParentPath);
        set(newObj, chatAttributes.userMessageRelPath, inputMessage);
        get(updatedData, chatAttributes.contextPath).push(newObj);
        dispatch(actions.setUpdatedObj(updatedData));
        onSave(clearxpath(cloneDeep(updatedData)), undefined, undefined, true);
        setInputMessage('');
    }, [updatedObj, chatAttributes, projectSchema, inputMessage, onSave]);

    // Render message function - moved before VirtualListItem
    const renderMessage = useCallback((type, content, contextIdentifier, field, mode) => {
        const context = chatContexts.find((o) => o[DB_ID] === contextIdentifier);
        const reasoning = get(context, chatAttributes.botReasoningRelPath);
        const isActive = contextIdentifier === contextId;
        const isEditing = mode === MODES.EDIT && isActive && editingField === field;

        return (
            <ChatMessage
                type={type}
                content={content}
                isActive={isActive}
                field={field}
                reasoning={reasoning}
                onEdit={handleStartEdit}
                onViewFull={handleOpenViewMessageDialog}
                onViewReasoning={handleOpenReasoningDialog}
                onCopy={handleCopyMessage}
                isEditing={isEditing}
                editText={editText}
                onEditChange={(e) => setEditText(e.target.value)}
                onSave={handleSaveEdit}
                onCancel={handleCancelEdit}
                mode={mode}
            />
        );
    }, [
        chatContexts,
        contextId,
        editingField,
        handleStartEdit,
        handleOpenViewMessageDialog,
        handleOpenReasoningDialog,
        handleCopyMessage,
        editText,
        handleSaveEdit,
        handleCancelEdit,
        mode
    ]);

    const collapsedClasses = useMemo(() => [
        styles.collapsedContainer,
        isDarkMode ? styles.dark : styles.light
    ].join(' '), [isDarkMode]);

    const chatContainerClasses = useMemo(() => [
        styles.chatContainer,
        isDarkMode ? styles.chatContainerDark : styles.chatContainerLight
    ].join(' '), [isDarkMode]);

    const headerClasses = useMemo(() => [
        styles.chatHeader,
        isDarkMode ? styles.chatHeaderDark : styles.chatHeaderLight
    ].join(' '), [isDarkMode]);

    // Handle loading state
    if (loading) {
        return <LoadingState />;
    }

    // Handle error state
    if (error) {
        return (
            <Box className={styles.emptyState}>
                <Alert severity="error" sx={{ width: '100%', maxWidth: 400 }}>
                    <Typography variant="body2">
                        {error.message || 'Failed to load conversation data'}
                    </Typography>
                </Alert>
            </Box>
        );
    }

    if (isCollapsed) {
        return (
            <Box className={collapsedClasses}>
                <Tooltip title="Show Conversation" placement="right">
                    <IconButton onClick={() => setIsCollapsed(false)} size="small">
                        <ChevronRight />
                    </IconButton>
                </Tooltip>
            </Box>
        );
    }

    if (!chatContexts || chatContexts.length === 0) {
        return (
            <Box className={styles.emptyState}>
                <Typography variant="body2" color="text.secondary">
                    No conversation data available
                </Typography>
            </Box>
        );
    }

    return (
        <Box
            className={chatContainerClasses}
            role="region"
            aria-label="Chat conversation view"
        >
            <ClipboardCopier text={clipboardText} />
            <Box className={headerClasses}>
                <Tooltip title="Hide Conversation">
                    <IconButton
                        onClick={() => setIsCollapsed(true)}
                        size="small"
                        aria-label="Hide conversation panel"
                    >
                        <ChevronLeft />
                    </IconButton>
                </Tooltip>
            </Box>

            <Box
                ref={messagesContainerRef}
                className={styles.messagesContainer}
                role="listbox"
                aria-label="Chat conversation list - use arrow keys to navigate, Enter to select"
                aria-activedescendant={contextId ? `context-${contextId}` : undefined}
                onKeyDown={handleKeyDown}
                tabIndex={0}
            >
                {
                    // For small lists, regular rendering is more efficient
                    chatContexts.map((context) => {
                        const currentContextId = context[DB_ID];
                        const isSelected = contextId === currentContextId;

                        // Create context classes inline to avoid React Hook Rule violation
                        const contextClasses = [
                            styles.contextWrapper,
                            isSelected ? styles.contextWrapperSelected : '',
                            isSelected && isDarkMode ? styles.contextWrapperSelectedDark : '',
                            isSelected && !isDarkMode ? styles.contextWrapperSelectedLight : '',
                            !isSelected && isDarkMode ? styles.contextWrapperHoverDark : '',
                            !isSelected && !isDarkMode ? styles.contextWrapperHoverLight : ''
                        ].filter(Boolean).join(' ');

                        const userMessage = get(context, chatAttributes.userMessageRelPath);
                        const botMessage = get(context, chatAttributes.botMessageRelPath);

                        return (
                            <Box
                                key={currentContextId}
                                id={`context-${currentContextId}`}
                                ref={(el) => {
                                    if (el) {
                                        contextElementsRef.current.set(currentContextId, el);
                                    } else {
                                        contextElementsRef.current.delete(currentContextId);
                                    }
                                }}
                                className={contextClasses}
                                onClick={() => handleContextSelect(currentContextId)}
                                tabIndex={-1}
                                role="option"
                                aria-selected={isSelected}
                                aria-label={`Chat context ${currentContextId}${isSelected ? ' (selected)' : ''}`}
                            >
                                {userMessage && renderMessage('user', userMessage, currentContextId, 'user_chat', mode)}
                                {botMessage && renderMessage('bot', botMessage, currentContextId, 'llm_chat', mode)}
                            </Box>
                        );
                    })
                }
            </Box>

            <Box className={styles.inputContainer} style={{ position: 'relative' }}>
                <TextField
                    fullWidth
                    multiline
                    maxRows={4}
                    placeholder="Type your message..."
                    value={inputMessage}
                    onChange={(e) => setInputMessage(e.target.value)}
                    onKeyDown={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                            e.preventDefault();
                            handleSend();
                        }
                    }}
                    disabled={mode === MODES.READ || editingField}
                    autoFocus={mode === MODES.EDIT}
                    InputProps={{
                        endAdornment: (
                            <InputAdornment position="end">
                                <IconButton
                                    onClick={handleSend}
                                    disabled={mode === MODES.READ || !inputMessage.trim()}
                                    size="small"
                                    aria-label="Send message"
                                >
                                    <Send />
                                </IconButton>
                            </InputAdornment>
                        ),
                    }}
                    size="small"
                    sx={{
                        '& .MuiInputBase-input': { fontSize: '0.75rem' },
                        '& .MuiInputBase-root': { fontSize: '0.75rem' }
                    }}
                />
                {(mode === MODES.READ || editingField) && (
                    <div
                        style={{
                            position: "absolute",
                            inset: 0, // shorthand for top:0,right:0,bottom:0,left:0
                            cursor: "text",
                        }}
                        onClick={() => {
                            if (mode === MODES.READ) {
                                onModeToggle();
                            }
                        }}
                    />
                )}
            </Box>

            <Dialog open={viewReasoningDialogOpen} onClose={handleCloseReasoningDialog} fullWidth maxWidth="md">
                <DialogContent>
                    <MarkdownRenderer
                        content={viewReasoningDialogContent}
                        variant="body2"
                    />
                </DialogContent>
            </Dialog>

            <Dialog open={viewMessageDialogOpen} onClose={handleCloseViewMessageDialog} fullWidth maxWidth="md">
                <DialogContent>
                    {mode === MODES.READ ? (
                        <MarkdownRenderer
                            content={viewMessageDialogContent}
                            variant="body2"
                        />
                    ) : (
                        <TextField
                            fullWidth
                            multiline
                            minRows={10}
                            value={modalEditText}
                            onChange={(e) => handleModalTextChange(e.target.value)}
                            variant="outlined"
                            placeholder="Enter your message..."
                            sx={{
                                '& .MuiInputBase-input': { fontSize: '0.75rem' },
                                '& .MuiInputBase-root': { fontSize: '0.75rem' }
                            }}
                        />
                    )}
                </DialogContent>
            </Dialog>
        </Box>
    );
}

// PropTypes for type checking
ChatView.propTypes = {
    modelName: PropTypes.string.isRequired,
    modelDataSource: PropTypes.shape({
        actions: PropTypes.object.isRequired,
        selector: PropTypes.func.isRequired
    }).isRequired
};

ErrorFallback.propTypes = {
    error: PropTypes.shape({
        message: PropTypes.string
    }).isRequired,
    resetErrorBoundary: PropTypes.func.isRequired
};

const MemoizedChatView = React.memo(ChatView);

// Wrap with ErrorBoundary for production safety
export default function ChatViewWithErrorBoundary(props) {
    return (
        <ErrorBoundary
            FallbackComponent={ErrorFallback}
            onError={(error, errorInfo) => {
                console.error('ChatView Error:', error);
                console.error('Error Info:', errorInfo);
            }}
        >
            <MemoizedChatView {...props} />
        </ErrorBoundary>
    );
}

// PropTypes for the ErrorBoundary wrapper
ChatViewWithErrorBoundary.propTypes = {
    modelName: PropTypes.string.isRequired,
    modelDataSource: PropTypes.shape({
        actions: PropTypes.object.isRequired,
        selector: PropTypes.func.isRequired
    }).isRequired
};