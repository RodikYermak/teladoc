import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MemoryRouter } from 'react-router-dom';
import { Header, TokenCard } from './App';

describe('TokenCard', () => {
    it('renders normal state', () => {
        render(<TokenCard used={400} total={1000} />);

        expect(screen.getByText('NORMAL')).toBeInTheDocument();
        expect(screen.queryByText('⚠ WARNING')).not.toBeInTheDocument();
        expect(screen.queryByText('OVER')).not.toBeInTheDocument();
    });

    it('renders warning state when usage is above 90%', () => {
        render(<TokenCard used={950} total={1000} />);

        expect(screen.getByText('⚠ WARNING')).toBeInTheDocument();
    });

    it('renders over state when usage exceeds quota', () => {
        render(<TokenCard used={1100} total={1000} />);

        expect(screen.getByText('OVER')).toBeInTheDocument();
    });
});

describe('Header', () => {
    it('hides admin link for non-admin users', () => {
        render(
            <MemoryRouter>
                <Header
                    auth={{
                        user: {
                            role: 'tenant',
                            display_name: 'Tenant 1 User',
                        },
                    }}
                    onLogout={vi.fn()}
                />
            </MemoryRouter>,
        );

        expect(screen.getByText('Admin View')).toHaveClass('nav-link-disabled');
        expect(screen.queryByRole('link', { name: 'Admin View' })).not.toBeInTheDocument();
    });

    it('shows admin link for admin users', () => {
        render(
            <MemoryRouter>
                <Header
                    auth={{
                        user: {
                            role: 'admin',
                            display_name: 'Admin User',
                        },
                    }}
                    onLogout={vi.fn()}
                />
            </MemoryRouter>,
        );

        expect(screen.getByRole('link', { name: 'Admin View' })).toBeInTheDocument();
    });
});