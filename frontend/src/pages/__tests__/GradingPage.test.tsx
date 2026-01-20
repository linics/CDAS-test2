import { render, screen } from '@testing-library/react';
import { vi } from 'vitest';

import GradingPage from '../GradingPage';

vi.mock('react-router-dom', () => ({
    useParams: () => ({ submissionId: '1' }),
    useNavigate: () => vi.fn(),
}));

const submission = {
    id: 1,
    assignment_id: 1,
    phase_index: 0,
    content_json: {},
    attachments_json: [],
    checkpoints_json: {},
};

const assignment = {
    id: 1,
    rubric_json: {
        dimensions: [
            { name: '问题与假设', weight: 20, description: 'desc' },
            { name: '资料检索与收集', weight: 20, description: 'desc' },
        ],
    },
};

vi.mock('@tanstack/react-query', () => ({
    useQuery: ({ queryKey }: any) => {
        if (Array.isArray(queryKey) && queryKey[0] === 'assignment') {
            return { data: { data: assignment } };
        }
        return { data: { data: submission } };
    },
    useMutation: () => ({ mutate: vi.fn(), isPending: false }),
    useQueryClient: () => ({ invalidateQueries: vi.fn() }),
}));

vi.mock('../../lib/api', () => ({
    submissionsApi: { getById: vi.fn() },
    assignmentsApi: { getById: vi.fn() },
    evaluationsApi: { aiAssist: vi.fn(), createTeacher: vi.fn() },
}));

test('renders four-level sliders with Chinese labels', () => {
    render(<GradingPage />);
    const sliders = screen.getAllByRole('slider');
    for (const slider of sliders) {
        expect(slider).toHaveAttribute('min', '1');
        expect(slider).toHaveAttribute('max', '4');
        expect(slider).toHaveAttribute('step', '1');
    }
    expect(screen.getAllByText(/优秀/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/良好/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/合格/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/需改进/).length).toBeGreaterThan(0);
});
