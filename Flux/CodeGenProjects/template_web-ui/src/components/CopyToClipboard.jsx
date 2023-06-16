import React, { useEffect, useRef } from 'react';

const CopyToClipboard = (props) => {
    const { text, copy } = props;
    const textRef = useRef(null);

    useEffect(() => {
        if (text && copy) {
            const textArea = textRef.current;
            textArea.select();
            if (document.queryCommandSupported('copy')) {
                document.execCommand('copy');
            }
        }
    }, [text, copy])

    return (
        <textarea ref={textRef} defaultValue={text} style={{ position: 'fixed', left: '-9999px', top: '-9999px', opacity: 0 }} readOnly />
    )
}

export default CopyToClipboard;