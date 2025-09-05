import React from 'react';
import ReactMarkdown from 'react-markdown';
import { Box, Typography, useTheme, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, Link } from '@mui/material';
import PropTypes from 'prop-types';

const MarkdownRenderer = ({ content, variant = 'body2' }) => {
    const theme = useTheme();
    const isDarkMode = theme.palette.mode === 'dark';

    const getMarkdownComponents = (textVariant) => ({
        p: ({ children }) => (
            <Typography
                variant={textVariant}
                component="p"
                sx={{
                    wordBreak: 'break-word',
                    lineHeight: 1.4,
                    margin: textVariant === 'body1' ? '0 0 16px 0' : 0,
                    '&:not(:last-child)': textVariant === 'body2' ? { marginBottom: 1 } : {},
                    '&:last-child': { margin: 0 }
                }}
            >
                {children}
            </Typography>
        ),
        h1: ({ children }) => (
            <Typography 
                variant={textVariant === 'body1' ? 'h5' : 'h6'} 
                component="h1" 
                sx={{ 
                    fontWeight: 'bold', 
                    margin: textVariant === 'body1' ? '16px 0 8px 0' : '8px 0 4px 0'
                }}
            >
                {children}
            </Typography>
        ),
        h2: ({ children }) => (
            <Typography 
                variant={textVariant === 'body1' ? 'h6' : 'subtitle1'} 
                component="h2" 
                sx={{ 
                    fontWeight: 'bold', 
                    margin: textVariant === 'body1' ? '12px 0 6px 0' : '6px 0 3px 0'
                }}
            >
                {children}
            </Typography>
        ),
        h3: ({ children }) => (
            <Typography 
                variant="subtitle2" 
                component="h3" 
                sx={{ 
                    fontWeight: 'bold', 
                    margin: textVariant === 'body1' ? '8px 0 4px 0' : '4px 0 2px 0'
                }}
            >
                {children}
            </Typography>
        ),
        strong: ({ children }) => (
            <Typography component="strong" sx={{ fontWeight: 'bold' }}>
                {children}
            </Typography>
        ),
        em: ({ children }) => (
            <Typography component="em" sx={{ fontStyle: 'italic' }}>
                {children}
            </Typography>
        ),
        code: ({ children, inline, className }) => {
            const language = className ? className.replace('language-', '') : '';
            return (
                <Typography
                    component={inline ? 'code' : 'pre'}
                    sx={{
                        fontFamily: '"Consolas", "Monaco", "Courier New", monospace',
                        backgroundColor: isDarkMode ? theme.palette.grey[800] : theme.palette.grey[100],
                        color: isDarkMode ? '#e6e6fa' : theme.palette.text.primary,
                        padding: inline ? '2px 6px' : (textVariant === 'body1' ? '8px' : '6px'),
                        borderRadius: inline ? '4px' : '8px',
                        fontSize: inline ? '0.8rem' : '0.8rem',
                        border: `1px solid ${isDarkMode ? theme.palette.grey[700] : theme.palette.grey[300]}`,
                        ...(inline ? {
                            display: 'inline',
                            verticalAlign: 'baseline'
                        } : {
                            display: 'block',
                            overflow: 'auto',
                            whiteSpace: 'pre',
                            margin: textVariant === 'body1' ? '12px 0' : '8px 0',
                            maxWidth: '100%',
                            lineHeight: 1.5,
                            position: 'relative'
                        }),
                        ...(language && !inline ? {
                            '&::before': {
                                content: `"${language}"`,
                                position: 'absolute',
                                top: '4px',
                                right: '8px',
                                fontSize: '0.75rem',
                                color: theme.palette.text.secondary,
                                textTransform: 'uppercase',
                                fontWeight: 'bold'
                            }
                        } : {})
                    }}
                >
                    {children}
                </Typography>
            );
        },
        ul: ({ children }) => (
            <Box component="ul" sx={{ 
                margin: textVariant === 'body1' ? '8px 0' : '4px 0', 
                paddingLeft: textVariant === 'body1' ? 3 : 2 
            }}>
                {children}
            </Box>
        ),
        ol: ({ children }) => (
            <Box component="ol" sx={{ 
                margin: textVariant === 'body1' ? '8px 0' : '4px 0', 
                paddingLeft: textVariant === 'body1' ? 3 : 2 
            }}>
                {children}
            </Box>
        ),
        li: ({ children }) => (
            <Typography component="li" variant={textVariant} sx={{ 
                margin: textVariant === 'body1' ? '4px 0' : '2px 0' 
            }}>
                {children}
            </Typography>
        ),
        blockquote: ({ children }) => (
            <Box
                component="blockquote"
                sx={{
                    borderLeft: `${textVariant === 'body1' ? '4px' : '3px'} solid ${theme.palette.grey[300]}`,
                    paddingLeft: 2,
                    margin: textVariant === 'body1' ? '16px 0' : '8px 0',
                    fontStyle: 'italic',
                    color: theme.palette.text.secondary
                }}
            >
                {children}
            </Box>
        ),
        a: ({ href, children }) => (
            <Link
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                sx={{
                    color: theme.palette.primary.main,
                    textDecoration: 'underline',
                    '&:hover': {
                        textDecoration: 'none'
                    }
                }}
            >
                {children}
            </Link>
        ),
        img: ({ src, alt }) => (
            <Box
                component="img"
                src={src}
                alt={alt}
                sx={{
                    maxWidth: '100%',
                    height: 'auto',
                    borderRadius: 1,
                    margin: textVariant === 'body1' ? '8px 0' : '4px 0'
                }}
            />
        ),
        hr: () => (
            <Box
                component="hr"
                sx={{
                    border: 'none',
                    height: '1px',
                    backgroundColor: theme.palette.divider,
                    margin: textVariant === 'body1' ? '16px 0' : '12px 0'
                }}
            />
        ),
        table: ({ children }) => (
            <TableContainer component={Paper} sx={{ margin: textVariant === 'body1' ? '16px 0' : '8px 0', maxWidth: '100%' }}>
                <Table size="small">
                    {children}
                </Table>
            </TableContainer>
        ),
        thead: ({ children }) => (
            <TableHead>
                {children}
            </TableHead>
        ),
        tbody: ({ children }) => (
            <TableBody>
                {children}
            </TableBody>
        ),
        tr: ({ children }) => (
            <TableRow>
                {children}
            </TableRow>
        ),
        th: ({ children }) => (
            <TableCell component="th" scope="col" sx={{ fontWeight: 'bold', backgroundColor: isDarkMode ? theme.palette.grey[800] : theme.palette.grey[50] }}>
                {children}
            </TableCell>
        ),
        td: ({ children }) => (
            <TableCell>
                {children}
            </TableCell>
        ),
        del: ({ children }) => (
            <Typography component="del" sx={{ textDecoration: 'line-through' }}>
                {children}
            </Typography>
        )
    });

    return (
        <ReactMarkdown components={getMarkdownComponents(variant)}>
            {content}
        </ReactMarkdown>
    );
};

MarkdownRenderer.propTypes = {
    content: PropTypes.string.isRequired,
    variant: PropTypes.oneOf(['body1', 'body2'])
};

export default MarkdownRenderer;