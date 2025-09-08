// MarkdownRenderer.jsx
import React, { useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import { useTheme } from '@mui/material/styles';
import PropTypes from 'prop-types';
import clsx from 'clsx';
import styles from './MarkdownRenderer.module.css';

const MarkdownRenderer = ({ content, variant = 'body2', className }) => {
    const theme = useTheme();
    const isDarkMode = theme.palette.mode === 'dark';

    // Memoize components to prevent recreation on every render
    const markdownComponents = useMemo(() => ({
        p: ({ children }) => (
            <p className={clsx(
                styles.paragraph,
                variant === 'body1' ? styles.paragraphLarge : styles.paragraphSmall
            )}>
                {children}
            </p>
        ),
        h1: ({ children }) => (
            <h1 className={clsx(
                styles.heading,
                styles.h1,
                variant === 'body1' ? styles.h1Large : styles.h1Small
            )}>
                {children}
            </h1>
        ),
        h2: ({ children }) => (
            <h2 className={clsx(
                styles.heading,
                styles.h2,
                variant === 'body1' ? styles.h2Large : styles.h2Small
            )}>
                {children}
            </h2>
        ),
        h3: ({ children }) => (
            <h3 className={clsx(
                styles.heading,
                styles.h3,
                variant === 'body1' ? styles.h3Large : styles.h3Small
            )}>
                {children}
            </h3>
        ),
        h4: ({ children }) => (
            <h4 className={clsx(
                styles.heading,
                styles.h4,
                variant === 'body1' ? styles.h4Large : styles.h4Small
            )}>
                {children}
            </h4>
        ),
        h5: ({ children }) => (
            <h5 className={clsx(
                styles.heading,
                styles.h5,
                variant === 'body1' ? styles.h5Large : styles.h5Small
            )}>
                {children}
            </h5>
        ),
        h6: ({ children }) => (
            <h6 className={clsx(
                styles.heading,
                styles.h6,
                variant === 'body1' ? styles.h6Large : styles.h6Small
            )}>
                {children}
            </h6>
        ),
        strong: ({ children }) => (
            <strong className={styles.strong}>{children}</strong>
        ),
        em: ({ children }) => (
            <em className={styles.emphasis}>{children}</em>
        ),
        del: ({ children }) => (
            <del className={styles.strikethrough}>{children}</del>
        ),
        // Fixed code component - properly handles inline vs block
        code: ({ children, className }) => {
            const isInline = !className;
            
            if (isInline) {
                // Inline code
                return (
                    <code 
                        className={clsx(
                            styles.inlineCode,
                            isDarkMode ? styles.inlineCodeDark : styles.inlineCodeLight
                        )}
                    >
                        {children}
                    </code>
                );
            }
            
            // Code block content (handled by pre)
            return children;
        },
        // Separate pre component for code blocks
        pre: ({ children }) => {
            const codeElement = React.Children.toArray(children)[0];
            const className = codeElement?.props?.className || '';
            const language = className.replace('language-', '');
            const codeContent = codeElement?.props?.children || '';
            
            return (
                <pre 
                    className={clsx(
                        styles.codeBlock,
                        isDarkMode ? styles.codeBlockDark : styles.codeBlockLight,
                        variant === 'body1' ? styles.codeBlockLarge : styles.codeBlockSmall
                    )}
                    data-language={language || undefined}
                >
                    <code className={styles.codeBlockContent}>
                        {codeContent}
                    </code>
                </pre>
            );
        },
        ul: ({ children, ordered }) => (
            <ul className={clsx(
                styles.list,
                styles.unorderedList,
                variant === 'body1' ? styles.listLarge : styles.listSmall
            )}>
                {children}
            </ul>
        ),
        ol: ({ children, ordered, start }) => (
            <ol 
                className={clsx(
                    styles.list,
                    styles.orderedList,
                    variant === 'body1' ? styles.listLarge : styles.listSmall
                )}
                start={start}
            >
                {children}
            </ol>
        ),
        li: ({ children, ordered }) => (
            <li className={clsx(
                styles.listItem,
                variant === 'body1' ? styles.listItemLarge : styles.listItemSmall
            )}>
                {children}
            </li>
        ),
        blockquote: ({ children }) => (
            <blockquote className={clsx(
                styles.blockquote,
                isDarkMode ? styles.blockquoteDark : styles.blockquoteLight,
                variant === 'body1' ? styles.blockquoteLarge : styles.blockquoteSmall
            )}>
                {children}
            </blockquote>
        ),
        a: ({ href, children }) => (
            <a 
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className={clsx(
                    styles.link,
                    isDarkMode ? styles.linkDark : styles.linkLight
                )}
                style={{ color: theme.palette.primary.main }}
            >
                {children}
            </a>
        ),
        img: ({ src, alt }) => (
            <img 
                src={src}
                alt={alt}
                className={clsx(
                    styles.image,
                    variant === 'body1' ? styles.imageLarge : styles.imageSmall
                )}
            />
        ),
        hr: () => (
            <hr className={clsx(
                styles.divider,
                isDarkMode ? styles.dividerDark : styles.dividerLight,
                variant === 'body1' ? styles.dividerLarge : styles.dividerSmall
            )} />
        ),
        table: ({ children }) => (
            <div className={clsx(
                styles.tableWrapper,
                variant === 'body1' ? styles.tableWrapperLarge : styles.tableWrapperSmall
            )}>
                <table className={clsx(
                    styles.table,
                    isDarkMode ? styles.tableDark : styles.tableLight
                )}>
                    {children}
                </table>
            </div>
        ),
        thead: ({ children }) => (
            <thead className={styles.tableHead}>
                {children}
            </thead>
        ),
        tbody: ({ children }) => (
            <tbody className={styles.tableBody}>
                {children}
            </tbody>
        ),
        tr: ({ children }) => (
            <tr className={styles.tableRow}>
                {children}
            </tr>
        ),
        th: ({ children, style }) => (
            <th 
                className={clsx(
                    styles.tableHeaderCell,
                    isDarkMode ? styles.tableHeaderCellDark : styles.tableHeaderCellLight
                )}
                style={style}
            >
                {children}
            </th>
        ),
        td: ({ children, style }) => (
            <td 
                className={clsx(
                    styles.tableCell,
                    isDarkMode ? styles.tableCellDark : styles.tableCellLight
                )}
                style={style}
            >
                {children}
            </td>
        )
    }), [isDarkMode, variant, theme.palette.primary.main]);

    return (
        <div className={clsx(
            styles.markdownContainer,
            isDarkMode ? styles.darkMode : styles.lightMode,
            className
        )}>
            <ReactMarkdown components={markdownComponents}>
                {content}
            </ReactMarkdown>
        </div>
    );
};

MarkdownRenderer.propTypes = {
    content: PropTypes.string.isRequired,
    variant: PropTypes.oneOf(['body1', 'body2']),
    className: PropTypes.string
};

export default MarkdownRenderer;