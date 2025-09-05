import React from 'react';
import {
    Box,
    Paper,
    IconButton,
    Tooltip,
    TextField,
    useTheme
} from '@mui/material';
import {
    Psychology,
    Edit,
    Check,
    Close,
    MoreHoriz,
    ContentCopy
} from '@mui/icons-material';
import MarkdownRenderer from './MarkdownRenderer';
import styles from './ChatView.module.css';

const TRUNCATE_LENGTH = 120;

function ChatMessage({
    type,
    content,
    isActive,
    field,
    reasoning,
    onEdit,
    onViewFull,
    onViewReasoning,
    onCopy,
    isEditing,
    editText,
    onEditChange,
    onSave,
    onCancel,
    mode
}) {
    const theme = useTheme();
    const isDarkMode = theme.palette.mode === 'dark';

    const isUser = type === 'user';
    const isBot = type === 'bot';

    const isTruncated = content && content.length > TRUNCATE_LENGTH;
    const displayText = (isTruncated && !isEditing)
        ? `${content.substring(0, TRUNCATE_LENGTH)}...`
        : content;

    const messageClasses = [
        styles.messageBubble,
        isUser ? styles.userMessage : styles.botMessage,
        !isUser && isDarkMode ? styles.botMessageDark : '',
        !isUser && !isDarkMode ? styles.botMessageLight : ''
    ].filter(Boolean).join(' ');

    const containerClasses = [
        styles.messageContainer,
        isUser ? styles.messageContainerUser : styles.messageContainerBot
    ].join(' ');

    const textColor = isUser ? theme.palette.primary.contrastText : theme.palette.text.primary;

    return (
        <Box className={containerClasses}>
            <Box className={styles.messageBubbleWrapper}>
                <Paper
                    elevation={0}
                    className={messageClasses}
                    sx={{ color: textColor }}
                >
                    <Box className={`${styles.messageText} ${isEditing ? styles.messageTextEditing : ''}`}>
                        {isEditing ? (
                            <TextField
                                variant="standard"
                                multiline
                                fullWidth
                                autoFocus
                                value={editText}
                                onChange={onEditChange}
                                InputProps={{ disableUnderline: true }}
                                inputProps={{
                                    style: {
                                        color: textColor,
                                        lineHeight: 1.4,
                                        fontSize: theme.typography.body2.fontSize,
                                        fontFamily: theme.typography.fontFamily,
                                    }
                                }}
                            />
                        ) : (
                            <MarkdownRenderer
                                content={displayText}
                                variant="body2"
                            />
                        )}
                    </Box>

                    {isEditing && (
                        <Box className={styles.editingButtons}>
                            <IconButton
                                size="small"
                                onClick={onSave}
                                sx={{ color: 'success.main' }}
                            >
                                <Check fontSize="small" />
                            </IconButton>
                            <IconButton
                                size="small"
                                onClick={onCancel}
                                sx={{ color: 'error.main' }}
                            >
                                <Close fontSize="small" />
                            </IconButton>
                        </Box>
                    )}
                </Paper>

                {/* Action buttons */}
                {!isEditing && (
                    <Box className={styles.actionButtons}>
                        {isBot && reasoning && (
                            <Tooltip title="View Reasoning">
                                <IconButton
                                    size="small"
                                    onClick={() => onViewReasoning(reasoning)}
                                    className={`${styles.actionIcon} ${styles.reasoningIcon}`}
                                >
                                    <Psychology fontSize="small" />
                                </IconButton>
                            </Tooltip>
                        )}
                        <Tooltip title="Copy message">
                            <IconButton
                                size="small"
                                onClick={() => onCopy(content)}
                                className={`${styles.actionIcon} ${styles.copyIcon}`}
                                sx={{ color: 'text.secondary' }}
                            >
                                <ContentCopy fontSize="small" />
                            </IconButton>
                        </Tooltip>
                        {isTruncated && (
                            <Tooltip title="View full message">
                                <IconButton
                                    size="small"
                                    onClick={() => onViewFull(content)}
                                    className={`${styles.actionIcon} ${styles.expandIcon}`}
                                    sx={{ color: 'text.secondary' }}
                                >
                                    <MoreHoriz fontSize="small" />
                                </IconButton>
                            </Tooltip>
                        )}
                        <Tooltip title="Edit message">
                            <IconButton
                                size="small"
                                onClick={() => onEdit(field)}
                                className={`${styles.actionIcon} ${styles.editIcon}`}
                                sx={{ color: 'text.secondary' }}
                                disabled={mode !== 'edit' || !isActive}
                            >
                                <Edit fontSize="small" />
                            </IconButton>
                        </Tooltip>
                    </Box>
                )}
            </Box>
        </Box>
    );
}

export default ChatMessage;