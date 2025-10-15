import React from 'react';
import Box from '@mui/material/Box';
import Paper from '@mui/material/Paper';
import IconButton from '@mui/material/IconButton';
import Tooltip from '@mui/material/Tooltip';
import TextField from '@mui/material/TextField';
import { useTheme } from '@mui/material/styles';
import Button from '@mui/material/Button';
import Psychology from '@mui/icons-material/Psychology';
import Edit from '@mui/icons-material/Edit';
import ContentCopy from '@mui/icons-material/ContentCopy';
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
    onCancel
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
                    sx={{ color: textColor, width: isEditing ? '100%' : 'max-content' }}
                >
                    <Box
                        className={isEditing ? styles.messageTextEditing : styles.messageText}
                        onDoubleClick={() => onViewFull(content, field)}
                        style={{ cursor: 'pointer' }}
                    >
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
                                        minHeight: '60px',
                                        overflow: 'auto',
                                        color: textColor,
                                        lineHeight: 1.4,
                                        fontSize: '0.75rem',
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
                            <Button
                                size="small"
                                onClick={onSave}
                                color='success'
                                variant='contained'
                            >
                                Save
                            </Button>
                            <Button
                                size="small"
                                onClick={onCancel}
                                color='error'
                                variant='contained'
                            >
                                Cancel
                            </Button>
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
                        <Tooltip title="Edit message">
                            <IconButton
                                size="small"
                                onClick={() => onEdit(field)}
                                className={`${styles.actionIcon} ${styles.editIcon}`}
                                sx={{ color: 'text.secondary' }}
                                disabled={!isActive}
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