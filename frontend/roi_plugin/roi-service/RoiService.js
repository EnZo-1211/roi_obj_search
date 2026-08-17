// RoiService.js - API service for ROI operations with smart sync/async handling
// Location: services/RoiService.js

/**
 * MD5 hash implementation for client-side use
 * Based on the RSA Data Security, Inc. MD5 Message-Digest Algorithm
 */
class MD5 {
    static hash(string) {
        function md5cycle(x, k) {
            let a = x[0], b = x[1], c = x[2], d = x[3];
            a = ff(a, b, c, d, k[0], 7, -680876936);
            d = ff(d, a, b, c, k[1], 12, -389564586);
            c = ff(c, d, a, b, k[2], 17, 606105819);
            b = ff(b, c, d, a, k[3], 22, -1044525330);
            a = ff(a, b, c, d, k[4], 7, -176418897);
            d = ff(d, a, b, c, k[5], 12, 1200080426);
            c = ff(c, d, a, b, k[6], 17, -1473231341);
            b = ff(b, c, d, a, k[7], 22, -45705983);
            a = ff(a, b, c, d, k[8], 7, 1770035416);
            d = ff(d, a, b, c, k[9], 12, -1958414417);
            c = ff(c, d, a, b, k[10], 17, -42063);
            b = ff(b, c, d, a, k[11], 22, -1990404162);
            a = ff(a, b, c, d, k[12], 7, 1804603682);
            d = ff(d, a, b, c, k[13], 12, -40341101);
            c = ff(c, d, a, b, k[14], 17, -1502002290);
            b = ff(b, c, d, a, k[15], 22, 1236535329);
            a = gg(a, b, c, d, k[1], 5, -165796510);
            d = gg(d, a, b, c, k[6], 9, -1069501632);
            c = gg(c, d, a, b, k[11], 14, 643717713);
            b = gg(b, c, d, a, k[0], 20, -373897302);
            a = gg(a, b, c, d, k[5], 5, -701558691);
            d = gg(d, a, b, c, k[10], 9, 38016083);
            c = gg(c, d, a, b, k[15], 14, -660478335);
            b = gg(b, c, d, a, k[4], 20, -405537848);
            a = gg(a, b, c, d, k[9], 5, 568446438);
            d = gg(d, a, b, c, k[14], 9, -1019803690);
            c = gg(c, d, a, b, k[3], 14, -187363961);
            b = gg(b, c, d, a, k[8], 20, 1163531501);
            a = gg(a, b, c, d, k[13], 5, -1444681467);
            d = gg(d, a, b, c, k[2], 9, -51403784);
            c = gg(c, d, a, b, k[7], 14, 1735328473);
            b = gg(b, c, d, a, k[12], 20, -1926607734);
            a = hh(a, b, c, d, k[5], 4, -378558);
            d = hh(d, a, b, c, k[8], 11, -2022574463);
            c = hh(c, d, a, b, k[11], 16, 1839030562);
            b = hh(b, c, d, a, k[14], 23, -35309556);
            a = hh(a, b, c, d, k[1], 4, -1530992060);
            d = hh(d, a, b, c, k[4], 11, 1272893353);
            c = hh(c, d, a, b, k[7], 16, -155497632);
            b = hh(b, c, d, a, k[10], 23, -1094730640);
            a = hh(a, b, c, d, k[13], 4, 681279174);
            d = hh(d, a, b, c, k[0], 11, -358537222);
            c = hh(c, d, a, b, k[3], 16, -722521979);
            b = hh(b, c, d, a, k[6], 23, 76029189);
            a = hh(a, b, c, d, k[9], 4, -640364487);
            d = hh(d, a, b, c, k[12], 11, -421815835);
            c = hh(c, d, a, b, k[15], 16, 530742520);
            b = hh(b, c, d, a, k[2], 23, -995338651);
            a = ii(a, b, c, d, k[0], 6, -198630844);
            d = ii(d, a, b, c, k[7], 10, 1126891415);
            c = ii(c, d, a, b, k[14], 15, -1416354905);
            b = ii(b, c, d, a, k[5], 21, -57434055);
            a = ii(a, b, c, d, k[12], 6, 1700485571);
            d = ii(d, a, b, c, k[3], 10, -1894986606);
            c = ii(c, d, a, b, k[10], 15, -1051523);
            b = ii(b, c, d, a, k[1], 21, -2054922799);
            a = ii(a, b, c, d, k[8], 6, 1873313359);
            d = ii(d, a, b, c, k[15], 10, -30611744);
            c = ii(c, d, a, b, k[6], 15, -1560198380);
            b = ii(b, c, d, a, k[13], 21, 1309151649);
            a = ii(a, b, c, d, k[4], 6, -145523070);
            d = ii(d, a, b, c, k[11], 10, -1120210379);
            c = ii(c, d, a, b, k[2], 15, 718787259);
            b = ii(b, c, d, a, k[9], 21, -343485551);
            x[0] = add32(a, x[0]);
            x[1] = add32(b, x[1]);
            x[2] = add32(c, x[2]);
            x[3] = add32(d, x[3]);
        }

        function cmn(q, a, b, x, s, t) {
            a = add32(add32(a, q), add32(x, t));
            return add32((a << s) | (a >>> (32 - s)), b);
        }

        function ff(a, b, c, d, x, s, t) {
            return cmn((b & c) | ((~b) & d), a, b, x, s, t);
        }

        function gg(a, b, c, d, x, s, t) {
            return cmn((b & d) | (c & (~d)), a, b, x, s, t);
        }

        function hh(a, b, c, d, x, s, t) {
            return cmn(b ^ c ^ d, a, b, x, s, t);
        }

        function ii(a, b, c, d, x, s, t) {
            return cmn(c ^ (b | (~d)), a, b, x, s, t);
        }

        function md51(s) {
            const n = s.length;
            const state = [1732584193, -271733879, -1732584194, 271733878];
            let i;
            for (i = 64; i <= s.length; i += 64) {
                md5cycle(state, md5blk(s.substring(i - 64, i)));
            }
            s = s.substring(i - 64);
            const tail = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
            for (i = 0; i < s.length; i++)
                tail[i >> 2] |= s.charCodeAt(i) << ((i % 4) << 3);
            tail[i >> 2] |= 0x80 << ((i % 4) << 3);
            if (i > 55) {
                md5cycle(state, tail);
                for (i = 0; i < 16; i++) tail[i] = 0;
            }
            tail[14] = n * 8;
            md5cycle(state, tail);
            return state;
        }

        function md5blk(s) {
            const md5blks = [];
            for (let i = 0; i < 64; i += 4) {
                md5blks[i >> 2] = s.charCodeAt(i)
                    + (s.charCodeAt(i + 1) << 8)
                    + (s.charCodeAt(i + 2) << 16)
                    + (s.charCodeAt(i + 3) << 24);
            }
            return md5blks;
        }

        function rhex(n) {
            let s = '';
            for (let j = 0; j < 4; j++)
                s += hex_chr[(n >> (j * 8 + 4)) & 0x0f]
                    + hex_chr[(n >> (j * 8)) & 0x0f];
            return s;
        }

        function hex(x) {
            for (let i = 0; i < x.length; i++)
                x[i] = rhex(x[i]);
            return x.join('');
        }

        function add32(a, b) {
            return (a + b) & 0xffffffff;
        }

        const hex_chr = '0123456789abcdef'.split('');

        return hex(md51(string));
    }
}

export class RoiService {
    constructor() {
        this.baseUrl = 'http://172.20.23.236:21000'; // Your FastAPI backend
        this.cache = new Map();
        this.cacheTimeout = 5 * 60 * 1000; // 5 minutes
        this.activeTasks = new Map(); // Track Celery tasks
    }

    /**
     * Perform ROI search - automatically handles sync/async based on section count
     * The backend /match-objects-async endpoint decides whether to use Celery or not
     * @param {Object} params - Search parameters__
     * @param {string} params.projectId - Project ID
     * @param {string} params.biosample - Brain biosample
     * @param {number} params.section - Section number
     * @param {Array} params.bbox - Bounding box [x1, y1, x2, y2]
     * @param {string} params.stain - Stain type (default: 'NISL')
     * @returns {Object} Results or task info based on processing mode
     */
    async searchROI(params) {
        // Try to get projectId from session storage if not provided
        const projectId = params.projectId || sessionStorage.getItem('projectId');
        const { biosample, section, bbox, stain = 'NISL' } = params;
        
        if (!projectId) {
            throw new Error('Project ID is required. Not found in params or session storage.');
        }

        try {
            // Always use the match-objects-async endpoint
            // It will decide sync vs async based on section count
            const response = await fetch(`${this.baseUrl}/match-objects-async`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    bbox: bbox,
                    stain: stain,
                    biosample: parseInt(biosample),
                    project_id: parseInt(projectId),
                    section: parseInt(section),
                    description: params.description
                })
            });

            if (!response.ok) {
                throw new Error(`ROI search failed: ${response.statusText}`);
            }

            const data = await response.json();
            
            // Check if it was processed synchronously or asynchronously
            if (data.processing_mode === 'sync' ) {
                // Synchronous processing completed immediately
                // Use hash value from backend response
                const hashValue = data.hash_value;
                console.log(`ROI Service: Using hash value from backend (sync): ${hashValue}`);
                return {
                    success: true,
                    processing_mode: 'sync',
                    message: data.message,
                    section_count: data.section_count,
                    results_url: `${this.baseUrl}/roi/results/${projectId}/${hashValue}`,
                    // Include data for embedded viewer instead of external URL
                    project_id: projectId,
                    hash_value: hashValue,
                    completed: true
                };
            } else {
                // Asynchronous processing - return task info with hash value
                console.log(`ROI Service: Using hash value from backend (async): ${data.hash_value}`);
                this.activeTasks.set(data.task_id, {
                    startTime: Date.now(),
                    params: params,
                    status: 'PENDING',
                    hash_value: data.hash_value // Store hash value for later use
                });
                
                return {
                    success: true,
                    processing_mode: 'async',
                    task_id: data.task_id,
                    message: data.message,
                    section_count: data.section_count,
                    estimated_time: data.estimated_time,
                    project_id: projectId,
                    hash_value: data.hash_value,
                    completed: false
                };
            }
        } catch (error) {
            console.error('RoiService: Error searching ROI:', error);
            throw error;
        }
    }

    /**
     * Generate MD5 hash for bbox (matching backend logic)
     * Backend uses: str(bbox) -> encode('utf-8') -> hashlib.md5() -> hexdigest()
     */
    generateHash(bbox) {
        // Convert bbox to string format that matches Python's str(bbox)
        // Python str([1, 2, 3, 4]) produces "[1, 2, 3, 4]" (with spaces after commas)
        const bboxStr = `[${bbox.join(', ')}]`;
        
        // Generate MD5 hash using the same algorithm as backend
        const hash = MD5.hash(bboxStr);
        
        console.log(`ROI Service: Generated MD5 hash for bbox ${bboxStr}: ${hash}`);
        return hash;
    }

    /**
     * Generate MD5 hash for any data (useful for task IDs, caching, etc.)
     */
    static generateMD5Hash(data) {
        // Convert data to string if it's not already
        const dataStr = typeof data === 'string' ? data : JSON.stringify(data);
        return MD5.hash(dataStr);
    }

    /**
     * Get available projects from database
     */
    async getProjects() {
        const cacheKey = 'projects';
        
        if (this.cache.has(cacheKey)) {
            const cached = this.cache.get(cacheKey);
            if (Date.now() - cached.timestamp < this.cacheTimeout) {
                console.log('RoiService: Using cached projects');
                return cached.data;
            }
        }

        try {
            // TODO: Update when backend endpoint is ready
            // For now, return mock data
            const mockProjects = [
                { id: 17358, name: 'Brain Atlas Project' },
                { id: 17359, name: 'Neuron Mapping Study' },
                { id: 17360, name: 'Tissue Analysis Research' }
            ];
            
            this.cache.set(cacheKey, {
                data: mockProjects,
                timestamp: Date.now()
            });

            return mockProjects;
        } catch (error) {
            console.error('RoiService: Error fetching projects:', error);
            throw error;
        }
    }

    /**
     * Get sections for a specific project
     */
    async getSections(projectId) {
        const cacheKey = `sections_${projectId}`;
        
        if (this.cache.has(cacheKey)) {
            const cached = this.cache.get(cacheKey);
            if (Date.now() - cached.timestamp < this.cacheTimeout) {
                console.log('RoiService: Using cached sections');
                return cached.data;
            }
        }

        try {
            // TODO: Update when backend endpoint is ready
            const mockSections = [
                { biosample: 15496, section: 100, stain: 'NISL' },
                { biosample: 15496, section: 200, stain: 'NISL' },
                { biosample: 15497, section: 150, stain: 'NISL' }
            ];
            
            this.cache.set(cacheKey, {
                data: mockSections,
                timestamp: Date.now()
            });

            return mockSections;
        } catch (error) {
            console.error('RoiService: Error fetching sections:', error);
            throw error;
        }
    }

    /**
     * Check status of a Celery task
     * @param {string} taskId - Celery task ID
     */
    async getTaskStatus(taskId) {
        try {
            const response = await fetch(`${this.baseUrl}/task-status/${taskId}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error(`Failed to get task status: ${response.statusText}`);
            }

            const status = await response.json();
            
            // Update stored task info
            if (this.activeTasks.has(taskId)) {
                const taskInfo = this.activeTasks.get(taskId);
                taskInfo.status = status.state;
                
                if (status.state === 'SUCCESS') {
                    // Task completed successfully - use hash value from when task was created
                    const hashValue = taskInfo.hash_value;
                    return {
                        ...status,
                        results_url: `${this.baseUrl}/roi/results/${taskInfo.params.projectId}/${hashValue}`,
                        // Include data for embedded viewer instead of external URL
                        project_id: taskInfo.params.projectId,
                        hash_value: hashValue
                    };
                }
            }

            return status;
        } catch (error) {
            console.error('RoiService: Error getting task status:', error);
            throw error;
        }
    }

    /**
     * Poll task status until completion
     * @param {string} taskId - Celery task ID
     * @param {number} interval - Polling interval in ms (default: 2000)
     * @param {number} timeout - Max time to wait in ms (default: 5 minutes)
     */
    async pollTaskStatus(taskId, interval = 2000, timeout = 300000) {
        const startTime = Date.now();
        
        return new Promise((resolve, reject) => {
            const checkStatus = async () => {
                try {
                    const status = await this.getTaskStatus(taskId);
                    
                    if (status.state === 'SUCCESS') {
                        resolve(status);
                        return;
                    }
                    
                    if (status.state === 'FAILURE') {
                        reject(new Error(status.error || 'Task failed'));
                        return;
                    }
                    
                    if (Date.now() - startTime > timeout) {
                        reject(new Error('Task timeout'));
                        return;
                    }
                    
                    // Continue polling
                    setTimeout(checkStatus, interval);
                    
                } catch (error) {
                    reject(error);
                }
            };
            
            checkStatus();
        });
    }

    /**
     * Get section count for a project
     */
    async getProjectSectionCount(projectId, stain = 'NISL') {
        try {
            const response = await fetch(
                `${this.baseUrl}/project/${projectId}/section-count?stain=${stain}`, 
                {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                }
            );

            if (!response.ok) {
                throw new Error(`Failed to get section count: ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.error('RoiService: Error getting section count:', error);
            throw error;
        }
    }

    /**
     * Get search results by project ID and hash
     */
    async getSearchResults(projectId, hashValue) {
        const cacheKey = `results_${projectId}_${hashValue}`;
        
        if (this.cache.has(cacheKey)) {
            const cached = this.cache.get(cacheKey);
            if (Date.now() - cached.timestamp < this.cacheTimeout) {
                console.log('RoiService: Using cached results');
                return cached.data;
            }
        }

        try {
            const response = await fetch(`${this.baseUrl}/roi/results/${projectId}/${hashValue}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error(`Failed to fetch results: ${response.statusText}`);
            }

            const data = await response.json();
            
            // Transform results for visualization
            const transformedData = this.transformResults(data);
            
            this.cache.set(cacheKey, {
                data: transformedData,
                timestamp: Date.now()
            });

            return transformedData;
        } catch (error) {
            console.error('RoiService: Error fetching results:', error);
            throw error;
        }
    }

    /**
     * Transform backend results for frontend visualization
     */
    transformResults(data) {
        if (!data || !data.results) {
            return { items: [] };
        }

        const items = [];
        
        // Parse the nested results structure: biosample -> stain -> sections
        Object.keys(data.results).forEach(biosample => {
            Object.keys(data.results[biosample]).forEach(stain => {
                const sections = data.results[biosample][stain];
                sections.forEach(sectionData => {
                    items.push({
                        id: `${biosample}_${sectionData.section}`,
                        biosample: biosample,
                        section: sectionData.section,
                        imageUrl: sectionData.image_url,
                        filename: sectionData.filename,
                        metadata: {
                            stain: stain,
                            project_id: data.project_id,
                            hash_value: data.hash_value
                        }
                    });
                });
            });
        });

        return {
            items: items,
            totalMatches: items.length,
            project_id: data.project_id,
            hash_value: data.hash_value,
            total_biosamples: data.total_biosamples,
            timestamp: Date.now()
        };
    }

    /**
     * Clear all cached data
     */
    clearCache() {
        this.cache.clear();
        console.log('RoiService: Cache cleared');
    }

    /**
     * Clear specific cache entry
     */
    clearCacheKey(key) {
        this.cache.delete(key);
        console.log(`RoiService: Cache cleared for key: ${key}`);
    }

    /**
     * Get completed searches with descriptions for dropdown
     */
    async getCompletedSearches(projectId = null, limit = 50) {
        try {
            const params = new URLSearchParams();
            if (projectId) {
                params.append('project_id', projectId);
            }
            params.append('limit', limit);

            const response = await fetch(`${this.baseUrl}/completed-searches?${params}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error(`Failed to fetch completed searches: ${response.statusText}`);
            }

            const data = await response.json();
            return data.searches || [];
        } catch (error) {
            console.error('RoiService: Error fetching completed searches:', error);
            return [];
        }
    }
}

// Export singleton instance
export const roiService = new RoiService();
export default RoiService;